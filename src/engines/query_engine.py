"""Query Engine - 查询引擎（QuerySpec → SQL）"""

import time
import hashlib
import json
import duckdb
from typing import List, Any, Dict, Optional, Tuple, Set
from src.models.query import QuerySpec, QueryResult, FilterCondition, DerivedField, RatioMetric
from src.engines.dataset_manager import get_dataset_manager
from src.core.config import settings
from src.utils.logger import log
from src.utils.security import SecurityValidator


class QueryExecutionError(Exception):
    """查询执行错误"""

    def __init__(self, message: str, sql: str | None = None, params: List[Any] | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.sql = sql
        self.params = params or []
        self.cause = str(cause) if cause else None


class QueryCache:
    """简单的内存查询缓存"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def _make_key(self, query_spec: QuerySpec) -> str:
        """生成缓存键"""
        spec_dict = query_spec.model_dump()
        spec_json = json.dumps(spec_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(spec_json.encode()).hexdigest()

    def get(self, query_spec: QuerySpec) -> Optional[QueryResult]:
        """获取缓存结果"""
        key = self._make_key(query_spec)
        if key in self.cache:
            entry = self.cache[key]
            # 检查是否过期
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                log.info(f"缓存命中: {key[:8]}...")
                return entry["result"]
            else:
                # 过期，删除
                del self.cache[key]
        return None

    def set(self, query_spec: QuerySpec, result: QueryResult):
        """设置缓存"""
        # 如果缓存已满，删除最旧的条目
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]

        key = self._make_key(query_spec)
        self.cache[key] = {
            "result": result,
            "timestamp": time.time()
        }
        log.info(f"缓存写入: {key[:8]}...")

    def clear(self):
        """清空缓存"""
        self.cache.clear()


class QueryEngine:
    """查询引擎"""

    def __init__(self):
        self.dataset_manager = get_dataset_manager()
        self.timeout = settings.query_timeout_seconds
        self.cache = QueryCache(max_size=100, ttl_seconds=300)

    def execute(self, query_spec: QuerySpec) -> QueryResult:
        """
        执行查询

        Args:
            query_spec: 查询规范

        Returns:
            QueryResult: 查询结果
        """
        log.info(f"执行查询: dataset={query_spec.dataset_id}")

        # 检查缓存
        cached_result = self.cache.get(query_spec)
        if cached_result:
            return cached_result

        start_time = time.time()

        # 验证数据集存在
        if not self.dataset_manager.dataset_exists(query_spec.dataset_id):
            raise ValueError(f"数据集不存在: {query_spec.dataset_id}")

        # 查询复杂度校验
        if not SecurityValidator.validate_query_complexity(query_spec.model_dump()):
            raise ValueError("查询复杂度超出限制")

        metadata = self.dataset_manager.get_schema(query_spec.dataset_id)
        self._validate_spec(query_spec, metadata)

        # 构建 SQL
        sql, params = self._build_sql(query_spec, metadata)
        log.debug(f"生成 SQL: {sql}")

        # 执行查询
        conn = self.dataset_manager._get_connection()
        try:
            result_df = conn.execute(sql, params).fetchdf()

            execution_time = (time.time() - start_time) * 1000

            result = QueryResult(
                columns=result_df.columns.tolist(),
                rows=result_df.values.tolist(),
                row_count=len(result_df),
                execution_time_ms=round(execution_time, 2)
            )

            # 写入缓存
            self.cache.set(query_spec, result)

            return result
        except Exception as e:
            log.error(f"查询执行失败: {e} | SQL: {sql} | params: {params}")
            raise QueryExecutionError("查询执行失败", sql=sql, params=params, cause=e) from e
        finally:
            conn.close()

    def _quote_identifier(self, name: str) -> str:
        """安全引用标识符"""
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    def _escape_like(self, value: str) -> str:
        """转义 LIKE 模式字符"""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _build_time_bucket(self, col: str, granularity: str) -> str:
        """构建时间分桶表达式"""
        return f"DATE_TRUNC('{granularity}', {self._quote_identifier(col)})"

    def _build_ratio_fields(self, ratios: List[RatioMetric]) -> List[DerivedField]:
        """构建比例/百分比衍生字段"""
        derived_fields: List[DerivedField] = []
        for ratio in ratios:
            expr = f"{ratio.numerator} / nullif({ratio.denominator}, 0)"
            if ratio.kind == "percent":
                expr = f"({expr}) * 100"
            if ratio.round is not None:
                expr = f"round({expr}, {ratio.round})"
            derived_fields.append(DerivedField(as_=ratio.as_, expr=expr))
        return derived_fields

    def _validate_spec(self, spec: QuerySpec, metadata) -> None:
        """校验查询字段与聚合合法性"""
        available_cols = {c.name for c in metadata.columns_schema}
        agg_aliases = {agg.as_ for agg in spec.aggregations}
        derived_aliases = {d.as_ for d in spec.derived}
        ratio_aliases = {r.as_ for r in spec.ratios}
        group_cols = list(spec.group_by)
        time_bucket_alias = None

        if spec.time_bucket:
            if spec.time_bucket.col not in available_cols:
                raise ValueError(f"时间分桶列不存在: {spec.time_bucket.col}")
            time_bucket_alias = spec.time_bucket.as_
            group_cols.append(time_bucket_alias)

        if spec.time_bucket and not (spec.group_by or spec.aggregations):
            raise ValueError("时间分桶需要与分组或聚合一起使用")

        if spec.having and not (spec.group_by or spec.aggregations or spec.time_bucket):
            raise ValueError("having 需要与分组或聚合一起使用")

        allowed_ratio_fields = available_cols | agg_aliases
        if time_bucket_alias:
            allowed_ratio_fields.add(time_bucket_alias)

        for ratio in spec.ratios:
            if ratio.numerator not in allowed_ratio_fields:
                raise ValueError(f"比例指标分子不存在: {ratio.numerator}")
            if ratio.denominator not in allowed_ratio_fields:
                raise ValueError(f"比例指标分母不存在: {ratio.denominator}")

        allowed_output_cols = set(group_cols) | agg_aliases | derived_aliases | ratio_aliases
        if spec.group_by or spec.aggregations or spec.time_bucket:
            allowed_sort = allowed_output_cols
        else:
            allowed_sort = available_cols | derived_aliases | ratio_aliases

        for col in spec.group_by:
            if col not in available_cols:
                raise ValueError(f"分组列不存在: {col}")

        for agg in spec.aggregations:
            if agg.col == "*" and agg.agg != "count":
                raise ValueError("仅 count 支持使用 * 作为聚合列")
            if agg.col != "*" and agg.col not in available_cols:
                raise ValueError(f"聚合列不存在: {agg.col}")

        for f in spec.filters:
            if f.col not in available_cols:
                raise ValueError(f"过滤列不存在: {f.col}")

        for h in spec.having:
            if h.col not in allowed_output_cols:
                raise ValueError(f"having 列不存在: {h.col}")

        if spec.top_k:
            if spec.top_k.by not in allowed_sort:
                raise ValueError(f"Top K 排序列不存在: {spec.top_k.by}")

        for s in spec.sort:
            if s.col not in allowed_sort:
                raise ValueError(f"排序列不存在: {s.col}")

    def _parse_expression(self, expr: str, allowed_identifiers: Set[str]) -> str:
        """安全解析表达式（仅允许白名单函数与字段）"""
        return SecurityValidator.parse_expression(expr, allowed_identifiers, self._quote_identifier)

    def _build_sql(self, spec: QuerySpec, metadata) -> Tuple[str, List[Any]]:
        """构建 SQL 语句"""
        table_name = self.dataset_manager.get_table_name(spec.dataset_id)

        derived_fields = list(spec.derived)
        if spec.ratios:
            derived_fields.extend(self._build_ratio_fields(spec.ratios))

        # SELECT 子句与 GROUP BY
        select_parts: List[str] = []
        output_columns: List[str] = []
        group_by_exprs: List[str] = []

        if spec.time_bucket:
            bucket_expr = self._build_time_bucket(spec.time_bucket.col, spec.time_bucket.granularity)
            select_parts.append(f'{bucket_expr} AS {self._quote_identifier(spec.time_bucket.as_)}')
            output_columns.append(spec.time_bucket.as_)
            group_by_exprs.append(bucket_expr)

        if spec.group_by:
            for col in spec.group_by:
                select_parts.append(f'{self._quote_identifier(col)} AS {self._quote_identifier(col)}')
                output_columns.append(col)
                group_by_exprs.append(self._quote_identifier(col))

        if spec.aggregations:
            for agg in spec.aggregations:
                if agg.agg == "nunique":
                    agg_expr = f'COUNT(DISTINCT {self._quote_identifier(agg.col)})'
                elif agg.agg == "count" and agg.col == "*":
                    agg_expr = "COUNT(*)"
                else:
                    agg_expr = f'{agg.agg.upper()}({self._quote_identifier(agg.col)})'
                select_parts.append(f'{agg_expr} AS {self._quote_identifier(agg.as_)}')
                output_columns.append(agg.as_)

        has_grouping = bool(group_by_exprs) or bool(spec.aggregations)

        if not has_grouping:
            select_parts = ["*"]
            output_columns = []

            if derived_fields or spec.having or spec.top_k or spec.sort:
                select_parts = [self._quote_identifier(c.name) for c in metadata.columns_schema]
                output_columns = [c.name for c in metadata.columns_schema]

        select_clause = ", ".join(select_parts)

        # FROM 子句
        from_clause = f'FROM {table_name}'

        # WHERE 子句
        where_clause = ""
        params: List[Any] = []
        if spec.filters:
            conditions = []
            for f in spec.filters:
                clause, clause_params = self._build_filter(f)
                conditions.append(clause)
                params.extend(clause_params)
            where_clause = f"WHERE {' AND '.join(conditions)}"

        # GROUP BY 子句
        group_clause = ""
        if has_grouping:
            group_clause = f"GROUP BY {', '.join(group_by_exprs)}"

        base_sql_parts = [
            f"SELECT {select_clause}",
            from_clause,
            where_clause,
            group_clause
        ]
        base_sql = " ".join(p for p in base_sql_parts if p)

        order_specs = []
        limit_value = spec.limit
        if spec.top_k:
            order_specs = [(spec.top_k.by, spec.top_k.order)]
            limit_value = spec.top_k.k
        elif spec.sort:
            order_specs = [(s.col, s.dir) for s in spec.sort]

        limit_clause = f"LIMIT {min(limit_value, settings.max_query_rows)}"
        order_clause = ""
        if order_specs:
            order_parts = [f'{self._quote_identifier(col)} {direction.upper()}' for col, direction in order_specs]
            order_clause = f"ORDER BY {', '.join(order_parts)}"

        if derived_fields or spec.having:
            allowed_identifiers = set(output_columns)
            derived_parts = [self._quote_identifier(col) for col in output_columns]
            for derived in derived_fields:
                expr = self._parse_expression(derived.expr, allowed_identifiers)
                derived_parts.append(f'{expr} AS {self._quote_identifier(derived.as_)}')
                allowed_identifiers.add(derived.as_)

            outer_where = ""
            if spec.having:
                having_conditions = []
                for h in spec.having:
                    clause, clause_params = self._build_filter(h)
                    having_conditions.append(clause)
                    params.extend(clause_params)
                outer_where = f"WHERE {' AND '.join(having_conditions)}"

            final_sql = f"SELECT {', '.join(derived_parts)} FROM ({base_sql}) AS subquery"
            if outer_where:
                final_sql = f"{final_sql} {outer_where}"
            if order_clause:
                final_sql = f"{final_sql} {order_clause}"
            final_sql = f"{final_sql} {limit_clause}"
            return final_sql, params

        base_sql_parts = [base_sql, order_clause, limit_clause]
        final_sql = " ".join(p for p in base_sql_parts if p)
        return final_sql, params

    def _build_filter(self, filter: FilterCondition) -> Tuple[str, List[Any]]:
        """构建过滤条件"""
        col = self._quote_identifier(filter.col)
        op = filter.op
        value = filter.value

        if op in {"=", "!=", ">", ">=", "<", "<="}:
            return f"{col} {op} ?", [value]
        if op == "in":
            if not isinstance(value, list) or not value:
                raise ValueError("in 操作符需要非空数组")
            placeholders = ", ".join(["?"] * len(value))
            return f"{col} IN ({placeholders})", list(value)
        if op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError("between 操作符需要长度为2的数组")
            return f"{col} BETWEEN ? AND ?", [value[0], value[1]]
        if op == "contains":
            if not isinstance(value, str):
                raise ValueError("contains 操作符需要字符串值")
            escaped = self._escape_like(value)
            return f"{col} LIKE ? ESCAPE '\\\\'", [f"%{escaped}%"]
        if op == "like":
            if not isinstance(value, str):
                raise ValueError("like 操作符需要字符串值")
            return f"{col} LIKE ?", [value]
        if op == "is_null":
            return f"{col} IS NULL", []
        raise ValueError(f"不支持的操作符: {op}")


# 全局单例
_query_engine = None


def get_query_engine() -> QueryEngine:
    """获取 QueryEngine 单例"""
    global _query_engine
    if _query_engine is None:
        _query_engine = QueryEngine()
    return _query_engine

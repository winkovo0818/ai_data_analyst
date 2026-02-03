"""Query Engine - 查询引擎（QuerySpec → SQL）"""

import time
import hashlib
import json
import re
import duckdb
from typing import List, Any, Dict, Optional, Tuple, Set
from src.models.query import QuerySpec, QueryResult, FilterCondition
from src.engines.dataset_manager import get_dataset_manager
from src.core.config import settings
from src.core.constants import ALLOWED_EXPR_FUNCTIONS
from src.utils.logger import log
from src.utils.security import SecurityValidator


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
            try:
                conn.execute(f"SET statement_timeout='{self.timeout}s'")
            except Exception as e:
                log.warning(f"设置查询超时失败: {e}")

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
            log.error(f"查询执行失败: {e}")
            raise
        finally:
            conn.close()

    def _quote_identifier(self, name: str) -> str:
        """安全引用标识符"""
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    def _escape_like(self, value: str) -> str:
        """转义 LIKE 模式字符"""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _validate_spec(self, spec: QuerySpec, metadata) -> None:
        """校验查询字段与聚合合法性"""
        available_cols = {c.name for c in metadata.columns_schema}
        agg_aliases = {agg.as_ for agg in spec.aggregations}
        derived_aliases = {d.as_ for d in spec.derived}
        if spec.group_by or spec.aggregations:
            allowed_sort = set(spec.group_by) | agg_aliases | derived_aliases
        else:
            allowed_sort = available_cols | derived_aliases

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

        for s in spec.sort:
            if s.col not in allowed_sort:
                raise ValueError(f"排序列不存在: {s.col}")

    def _normalize_expression(self, expr: str, allowed_identifiers: Set[str]) -> str:
        """验证并规范化表达式（仅允许白名单函数与字段）"""
        if not SecurityValidator.validate_expression(expr):
            raise ValueError("表达式包含非法内容")

        if not re.fullmatch(r"[0-9A-Za-z_\u4e00-\u9fa5\s\+\-\*\/\(\),\.]+", expr):
            raise ValueError("表达式包含非法字符")

        identifiers = re.findall(r"[A-Za-z_\u4e00-\u9fa5][\w\u4e00-\u9fa5]*", expr)
        for ident in identifiers:
            if ident.lower() in ALLOWED_EXPR_FUNCTIONS:
                continue
            if ident not in allowed_identifiers:
                raise ValueError(f"表达式包含未授权字段: {ident}")

        def replace_ident(match: re.Match) -> str:
            ident = match.group(0)
            if ident.lower() in ALLOWED_EXPR_FUNCTIONS:
                return ident
            if ident in allowed_identifiers:
                return self._quote_identifier(ident)
            return ident

        return re.sub(r"[A-Za-z_\u4e00-\u9fa5][\w\u4e00-\u9fa5]*", replace_ident, expr)

    def _build_sql(self, spec: QuerySpec, metadata) -> Tuple[str, List[Any]]:
        """构建 SQL 语句"""
        table_name = self.dataset_manager.get_table_name(spec.dataset_id)

        # SELECT 子句
        select_parts = []
        output_columns = []

        if spec.group_by:
            # 分组查询
            for col in spec.group_by:
                select_parts.append(f'{self._quote_identifier(col)} AS {self._quote_identifier(col)}')
                output_columns.append(col)

            for agg in spec.aggregations:
                if agg.agg == "nunique":
                    agg_expr = f'COUNT(DISTINCT {self._quote_identifier(agg.col)})'
                elif agg.agg == "count" and agg.col == "*":
                    agg_expr = "COUNT(*)"
                else:
                    agg_expr = f'{agg.agg.upper()}({self._quote_identifier(agg.col)})'
                select_parts.append(f'{agg_expr} AS {self._quote_identifier(agg.as_)}')
                output_columns.append(agg.as_)
        else:
            # 非分组查询
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
            else:
                select_parts.append("*")

        # 如果存在衍生字段且当前使用 *, 展开为显式列
        if spec.derived and select_parts == ["*"]:
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
        if spec.group_by:
            group_cols = ", ".join([self._quote_identifier(col) for col in spec.group_by])
            group_clause = f"GROUP BY {group_cols}"

        # ORDER BY 子句
        order_clause = ""
        if spec.sort:
            order_parts = [f'{self._quote_identifier(s.col)} {s.dir.upper()}' for s in spec.sort]
            order_clause = f"ORDER BY {', '.join(order_parts)}"

        # LIMIT 子句
        limit_clause = f"LIMIT {min(spec.limit, settings.max_query_rows)}"

        # 组合 SQL
        sql_parts = [
            f"SELECT {select_clause}",
            from_clause,
            where_clause,
            group_clause,
            order_clause,
            limit_clause
        ]

        # 处理衍生字段（需要嵌套查询）
        if spec.derived:
            base_sql_parts = [
                f"SELECT {select_clause}",
                from_clause,
                where_clause,
                group_clause
            ]
            base_sql = " ".join(p for p in base_sql_parts if p)
            allowed_identifiers = {c.name for c in metadata.columns_schema}
            allowed_identifiers.update({agg.as_ for agg in spec.aggregations})

            derived_parts = [self._quote_identifier(col) for col in output_columns]
            for derived in spec.derived:
                expr = self._normalize_expression(derived.expr, allowed_identifiers)
                derived_parts.append(f'{expr} AS {self._quote_identifier(derived.as_)}')

            final_sql = f"SELECT {', '.join(derived_parts)} FROM ({base_sql}) AS subquery"
            if order_clause:
                final_sql = f"{final_sql} {order_clause}"
            final_sql = f"{final_sql} {limit_clause}"
            return final_sql, params

        base_sql = " ".join(p for p in sql_parts if p)
        return base_sql, params

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

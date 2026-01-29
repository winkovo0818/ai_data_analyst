"""Query Engine - 查询引擎（QuerySpec → SQL）"""

import time
import hashlib
import json
import duckdb
from typing import List, Any, Dict, Optional
from src.models.query import QuerySpec, QueryResult, FilterCondition
from src.engines.dataset_manager import get_dataset_manager
from src.core.config import settings
from src.core.constants import ALLOWED_FILTER_OPERATORS, ALLOWED_AGGREGATIONS
from src.utils.logger import log


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

        # 构建 SQL
        sql = self._build_sql(query_spec)
        log.debug(f"生成 SQL: {sql}")

        # 执行查询
        conn = self.dataset_manager._get_connection()
        try:
            result_df = conn.execute(sql).fetchdf()

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

    def _build_sql(self, spec: QuerySpec) -> str:
        """构建 SQL 语句"""
        table_name = self.dataset_manager.get_table_name(spec.dataset_id)

        # SELECT 子句
        select_parts = []

        if spec.group_by:
            # 分组查询
            for col in spec.group_by:
                select_parts.append(f'"{col}"')

            for agg in spec.aggregations:
                agg_expr = f'{agg.agg.upper()}("{agg.col}")'
                select_parts.append(f'{agg_expr} AS "{agg.as_}"')
        else:
            # 非分组查询
            if spec.aggregations:
                for agg in spec.aggregations:
                    agg_expr = f'{agg.agg.upper()}("{agg.col}")'
                    select_parts.append(f'{agg_expr} AS "{agg.as_}"')
            else:
                select_parts.append("*")

        select_clause = ", ".join(select_parts)

        # FROM 子句
        from_clause = f'FROM {table_name}'

        # WHERE 子句
        where_clause = ""
        if spec.filters:
            conditions = [self._build_filter(f) for f in spec.filters]
            where_clause = f"WHERE {' AND '.join(conditions)}"

        # GROUP BY 子句
        group_clause = ""
        if spec.group_by:
            group_cols = ", ".join([f'"{col}"' for col in spec.group_by])
            group_clause = f"GROUP BY {group_cols}"

        # ORDER BY 子句
        order_clause = ""
        if spec.sort:
            order_parts = [f'"{s.col}" {s.dir.upper()}' for s in spec.sort]
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
        base_sql = " ".join(p for p in sql_parts if p)

        if spec.derived:
            derived_parts = []
            for col in select_parts:
                # 提取原始列名
                if " AS " in col:
                    derived_parts.append(col.split(" AS ")[1].strip('"'))
                else:
                    derived_parts.append(col.strip('"'))

            for derived in spec.derived:
                derived_parts.append(f'{derived.expr} AS "{derived.as_}"')

            final_sql = f"SELECT {', '.join(derived_parts)} FROM ({base_sql}) AS subquery"
            return final_sql

        return base_sql

    def _build_filter(self, filter: FilterCondition) -> str:
        """构建过滤条件"""
        col = f'"{filter.col}"'
        op = filter.op
        value = filter.value

        if op == "=":
            return f"{col} = {self._format_value(value)}"
        elif op == "!=":
            return f"{col} != {self._format_value(value)}"
        elif op == ">":
            return f"{col} > {self._format_value(value)}"
        elif op == ">=":
            return f"{col} >= {self._format_value(value)}"
        elif op == "<":
            return f"{col} < {self._format_value(value)}"
        elif op == "<=":
            return f"{col} <= {self._format_value(value)}"
        elif op == "in":
            values = ", ".join([self._format_value(v) for v in value])
            return f"{col} IN ({values})"
        elif op == "between":
            return f"{col} BETWEEN {self._format_value(value[0])} AND {self._format_value(value[1])}"
        elif op == "contains":
            return f"{col} LIKE '%{value}%'"
        elif op == "is_null":
            return f"{col} IS NULL"
        else:
            raise ValueError(f"不支持的操作符: {op}")

    def _format_value(self, value: Any) -> str:
        """格式化值"""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            # 转义单引号
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        else:
            return str(value)


# 全局单例
_query_engine = None


def get_query_engine() -> QueryEngine:
    """获取 QueryEngine 单例"""
    global _query_engine
    if _query_engine is None:
        _query_engine = QueryEngine()
    return _query_engine

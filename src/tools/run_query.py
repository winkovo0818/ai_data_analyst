"""Tool 定义：run_query"""

from pydantic import BaseModel, Field
from src.models.query import QuerySpec, QueryResult


class RunQueryInput(QuerySpec):
    """执行查询输入（继承 QuerySpec）"""
    pass


class RunQueryOutput(QueryResult):
    """执行查询输出（继承 QueryResult）"""
    pass


# Tool 元数据
TOOL_NAME = "run_query"
TOOL_DESCRIPTION = """
执行结构化查询（基于 QuerySpec DSL）。

参数：
- dataset_id: 数据集ID
- filters: 过滤条件数组（可选）
  - col: 列名
  - op: 操作符（=, !=, >, >=, <, <=, in, between, contains, like, is_null）
  - value: 过滤值
- group_by: 分组列名数组（可选）
- aggregations: 聚合操作数组（可选）
  - as: 结果列名
  - agg: 聚合函数（sum, avg, min, max, count, nunique）
  - col: 聚合列名
- time_bucket: 时间分桶（可选）
  - col: 时间列名
  - granularity: 分桶粒度（hour, day, week, month, quarter, year）
  - as: 结果列名
- having: 聚合后过滤条件数组（可选）
  - col: 列名（聚合别名/分组列）
  - op: 操作符（=, !=, >, >=, <, <=, in, between, contains, like, is_null）
  - value: 过滤值
- top_k: Top K 规则（可选）
  - by: 排序列名
  - k: Top K 数量
  - order: 排序方向（asc, desc）
- derived: 衍生字段数组（可选）
  - as: 结果列名
  - expr: 计算表达式（支持 +, -, *, /, nullif, coalesce, round, abs）
- ratios: 比例/百分比指标（可选）
  - as: 结果列名
  - numerator: 分子列名或别名
  - denominator: 分母列名或别名
  - kind: ratio 或 percent
  - round: 小数位数（可选）
- sort: 排序规则数组（可选）
  - col: 排序列名
  - dir: 排序方向（asc, desc）
- limit: 返回行数限制（默认5000，最大10000）

返回：
- columns: 结果列名
- rows: 结果数据
- row_count: 返回行数
- execution_time_ms: 执行耗时

安全约束：
1. 不允许执行任意 SQL
2. 所有操作符和函数都在白名单内
3. 最大返回 10000 行
4. 自动超时保护

使用场景：
1. 数据聚合（按维度汇总）
2. 数据过滤（筛选特定条件）
3. 数据计算（衍生指标）
4. 数据排序（找出 Top N）
"""

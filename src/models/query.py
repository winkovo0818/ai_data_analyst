"""查询相关模型"""

from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator
from src.core.constants import (
    ALLOWED_FILTER_OPERATORS,
    ALLOWED_AGGREGATIONS,
    ALLOWED_EXPR_FUNCTIONS,
    TIME_BUCKET_GRAINULARITIES
)


class FilterCondition(BaseModel):
    """过滤条件"""
    col: str = Field(..., description="列名")
    op: str = Field(..., description="操作符: =, !=, >, >=, <, <=, in, between, contains, is_null")
    value: Any = Field(None, description="过滤值")

    @field_validator('op')
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in ALLOWED_FILTER_OPERATORS:
            raise ValueError(f"不支持的操作符: {v}. 允许的操作符: {ALLOWED_FILTER_OPERATORS}")
        return v


class Aggregation(BaseModel):
    """聚合定义"""
    as_: str = Field(..., alias="as", description="结果列名")
    agg: str = Field(..., description="聚合函数: sum, avg, min, max, count, nunique")
    col: str = Field(..., description="聚合列名")

    @field_validator('agg')
    @classmethod
    def validate_agg_function(cls, v: str) -> str:
        if v not in ALLOWED_AGGREGATIONS:
            raise ValueError(f"不支持的聚合函数: {v}. 允许的函数: {ALLOWED_AGGREGATIONS}")
        return v


class DerivedField(BaseModel):
    """衍生字段"""
    as_: str = Field(..., alias="as", description="结果列名")
    expr: str = Field(..., description="计算表达式")

    @field_validator('expr')
    @classmethod
    def validate_expression(cls, v: str) -> str:
        # 简单的白名单检查（实际应更严格）
        import re
        # 移除空格和常见符号
        cleaned = re.sub(r'[\s\(\),]', '', v)
        # 仅允许基础字符与运算符（防止引号与分号）
        if not re.fullmatch(r"[0-9A-Za-z_\u4e00-\u9fa5\s\+\-\*\/\(\),\.]+", v):
            raise ValueError("表达式包含非法字符")
        # 检查是否包含非法函数或关键字
        dangerous = ['exec', 'eval', 'import', 'open', 'file', '__']
        for d in dangerous:
            if d in v.lower():
                raise ValueError(f"表达式包含非法内容: {d}")
        return v


class TimeBucket(BaseModel):
    """时间分桶"""
    col: str = Field(..., description="时间列名")
    granularity: str = Field(..., description="分桶粒度: hour, day, week, month, quarter, year")
    as_: str = Field("time_bucket", alias="as", description="结果列名")

    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        if v not in TIME_BUCKET_GRAINULARITIES:
            raise ValueError(f"不支持的分桶粒度: {v}. 允许的粒度: {TIME_BUCKET_GRAINULARITIES}")
        return v


class TopKSpec(BaseModel):
    """Top K 规则"""
    by: str = Field(..., description="排序列名")
    k: int = Field(..., ge=1, le=10000, description="Top K 数量")
    order: Literal["asc", "desc"] = Field("desc", description="排序方向")


class RatioMetric(BaseModel):
    """比例/百分比指标"""
    as_: str = Field(..., alias="as", description="结果列名")
    numerator: str = Field(..., description="分子列名或别名")
    denominator: str = Field(..., description="分母列名或别名")
    kind: Literal["ratio", "percent"] = Field("ratio", description="指标类型")
    round: Optional[int] = Field(None, ge=0, le=6, description="小数位数（可选）")


class SortSpec(BaseModel):
    """排序规则"""
    col: str = Field(..., description="排序列名")
    dir: Literal["asc", "desc"] = Field("asc", description="排序方向")


class QuerySpec(BaseModel):
    """查询规范（DSL）"""
    dataset_id: str = Field(..., description="数据集ID")
    filters: List[FilterCondition] = Field(default_factory=list, description="过滤条件")
    group_by: List[str] = Field(default_factory=list, description="分组列")
    aggregations: List[Aggregation] = Field(default_factory=list, description="聚合操作")
    derived: List[DerivedField] = Field(default_factory=list, description="衍生字段")
    ratios: List[RatioMetric] = Field(default_factory=list, description="比例/百分比指标")
    time_bucket: Optional[TimeBucket] = Field(None, description="时间分桶")
    having: List[FilterCondition] = Field(default_factory=list, description="聚合后过滤条件")
    top_k: Optional[TopKSpec] = Field(None, description="Top K 规则")
    sort: List[SortSpec] = Field(default_factory=list, description="排序规则")
    limit: int = Field(5000, ge=1, le=10000, description="返回行数限制")


class QueryResult(BaseModel):
    """查询结果"""
    columns: List[str] = Field(..., description="结果列名")
    rows: List[List[Any]] = Field(..., description="结果数据")
    row_count: int = Field(..., description="返回行数")
    execution_time_ms: float = Field(0.0, description="执行耗时（毫秒）")

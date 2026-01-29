"""Tool 定义：resolve_fields"""

from typing import List
from pydantic import BaseModel, Field


class ResolveFieldsInput(BaseModel):
    """字段语义映射输入"""
    dataset_id: str = Field(..., description="数据集ID")
    terms: List[str] = Field(..., description="语义关键词列表")


class ResolveFieldsOutput(BaseModel):
    """字段语义映射输出"""
    mapped_columns: List[str] = Field(..., description="匹配到的列名列表")
    suggestions: dict = Field(default_factory=dict, description="建议的字段映射")


# Tool 元数据
TOOL_NAME = "resolve_fields"
TOOL_DESCRIPTION = """
将用户提到的语义关键词映射到实际的数据集列名。

参数：
- dataset_id: 数据集ID
- terms: 语义关键词列表（如："退货原因", "质量问题"）

返回：
- mapped_columns: 匹配到的实际列名列表
- suggestions: 建议的字段映射关系

使用场景：
1. 用户使用自然语言描述字段
2. 字段名称不明确时的语义匹配
3. 多语言字段名映射

示例：
输入：terms=["退货原因", "质量问题"]
输出：mapped_columns=["产品质量", "物流异常", "购买风险"]
"""

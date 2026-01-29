"""Tool 定义：sample_rows"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class SampleRowsInput(BaseModel):
    """获取样本数据输入"""
    dataset_id: str = Field(..., description="数据集ID")
    n: int = Field(5, ge=1, le=100, description="返回行数（1-100）")
    columns: Optional[List[str]] = Field(None, description="指定列名（可选，默认全部列）")


class SampleRowsOutput(BaseModel):
    """获取样本数据输出"""
    columns: List[str] = Field(..., description="列名列表")
    rows: List[List[Any]] = Field(..., description="数据行")
    total_rows: int = Field(..., description="数据集总行数")


# Tool 元数据
TOOL_NAME = "sample_rows"
TOOL_DESCRIPTION = """
获取数据集的样本行数据。

参数：
- dataset_id: 数据集ID
- n: 返回行数（默认5行，最多100行）
- columns: 指定列名列表（可选，默认返回所有列）

返回：
- columns: 列名列表
- rows: 数据行数组
- total_rows: 数据集总行数

使用场景：
1. 查看实际数据内容
2. 理解数据格式
3. 确认字段值范围
"""

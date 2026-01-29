"""Tool 定义：get_schema"""

from pydantic import BaseModel, Field
from src.models.dataset import ColumnSchema
from typing import List


class GetSchemaInput(BaseModel):
    """获取 Schema 输入"""
    dataset_id: str = Field(..., description="数据集ID")


class GetSchemaOutput(BaseModel):
    """获取 Schema 输出"""
    dataset_id: str = Field(..., description="数据集ID")
    columns: List[ColumnSchema] = Field(..., description="列 Schema 信息")
    row_count: int = Field(..., description="总行数")


# Tool 元数据
TOOL_NAME = "get_schema"
TOOL_DESCRIPTION = """
获取数据集的字段结构与统计信息。

参数：
- dataset_id: 数据集ID

返回：
- columns: 列信息数组，包含列名、类型、空值比例、示例值等
- row_count: 数据集总行数

使用场景：
1. 理解数据集结构
2. 确认字段名称和类型
3. 了解数据质量（空值比例）
"""

"""Tool 定义：create_dataset"""

from typing import Optional
from pydantic import BaseModel, Field


class CreateDatasetInput(BaseModel):
    """创建数据集输入"""
    file_id: str = Field(..., description="文件ID（上传后返回）")
    sheet: Optional[str] = Field(None, description="Excel Sheet 名称（仅 Excel）")
    header_row: int = Field(1, ge=1, description="表头所在行号")


class CreateDatasetOutput(BaseModel):
    """创建数据集输出"""
    dataset_id: str = Field(..., description="数据集唯一标识")
    row_count: int = Field(..., description="数据行数")
    column_count: int = Field(..., description="列数")


# Tool 元数据
TOOL_NAME = "create_dataset"
TOOL_DESCRIPTION = """
注册上传的文件为数据集。

参数：
- file_id: 上传文件后返回的文件ID
- sheet: Excel 文件的 Sheet 名称（可选，默认第一个 Sheet）
- header_row: 表头所在行号（默认第1行）

返回：
- dataset_id: 数据集ID，用于后续查询和分析
"""

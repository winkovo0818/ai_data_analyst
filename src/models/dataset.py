"""数据集相关模型"""

from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """列 Schema"""
    name: str = Field(..., description="列名")
    type: str = Field(..., description="数据类型: int, float, string, boolean, datetime")
    null_ratio: float = Field(0.0, ge=0.0, le=1.0, description="空值比例")
    example_values: List[Any] = Field(default_factory=list, description="示例值")
    unique_count: Optional[int] = Field(None, description="唯一值数量")
    min_value: Optional[Any] = Field(None, description="最小值（数值/日期类型）")
    max_value: Optional[Any] = Field(None, description="最大值（数值/日期类型）")


class DatasetMetadata(BaseModel):
    """数据集元数据"""
    dataset_id: str = Field(..., description="数据集唯一标识")
    source_type: str = Field(..., description="来源类型: excel, csv")
    original_filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="存储路径")
    sheet_name: Optional[str] = Field(None, description="Excel Sheet 名称")
    row_count: int = Field(..., ge=0, description="总行数")
    column_count: int = Field(..., ge=0, description="总列数")
    columns_schema: List[ColumnSchema] = Field(default_factory=list, description="列 Schema")  # 改名避免冲突
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    size_bytes: int = Field(0, ge=0, description="文件大小（字节）")

    model_config = {"arbitrary_types_allowed": True}


class DatasetSample(BaseModel):
    """数据集样本"""
    columns: List[str] = Field(..., description="列名列表")
    rows: List[List[Any]] = Field(..., description="数据行")
    total_rows: int = Field(..., description="数据集总行数")

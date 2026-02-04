"""API 响应模型"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TableResult(BaseModel):
    """表格结果"""
    name: str = Field(..., description="表格名称")
    columns: List[str] = Field(..., description="列名")
    rows: List[List[Any]] = Field(..., description="数据行")


class AuditInfo(BaseModel):
    """审计信息"""
    trace_id: str = Field(..., description="追踪ID")
    steps: List[Dict[str, Any]] = Field(..., description="执行步骤")
    total_steps: int = Field(..., description="总步数")
    llm_tokens: int = Field(0, description="LLM token 消耗")
    llm_cost_usd: float = Field(0.0, description="LLM 成本（美元）")
    duration_ms: float = Field(0.0, description="总耗时（毫秒）")


class AnalysisResponse(BaseModel):
    """分析响应（统一结构）"""
    answer: str = Field(..., description="自然语言答案")
    tables: List[TableResult] = Field(default_factory=list, description="表格结果")
    charts: List[Dict[str, Any]] = Field(default_factory=list, description="图表结果")
    audit: AuditInfo = Field(..., description="审计信息")
    success: bool = Field(True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_detail: Optional[Dict[str, Any]] = Field(None, description="错误详情")


class UploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    size_bytes: int = Field(..., description="文件大小")
    sheets: Optional[List[str]] = Field(None, description="Excel sheet 列表")

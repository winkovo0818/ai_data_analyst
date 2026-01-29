"""图表相关模型"""

from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field
from src.core.constants import CHART_TYPES


class PlotSpec(BaseModel):
    """图表规范"""
    chart_type: str = Field(..., description="图表类型: line, bar, pie, scatter, area")
    title: str = Field(..., description="图表标题")
    x: Optional[str] = Field(None, description="X轴列名")
    y: Optional[str] = Field(None, description="Y轴列名")
    series: Optional[str] = Field(None, description="系列分组列名")
    y_format: Optional[Literal["number", "percent", "currency"]] = Field("number", description="Y轴格式")
    data: List[Dict[str, Any]] = Field(..., description="图表数据")

    def model_post_init(self, __context):
        """模型初始化后验证"""
        if self.chart_type not in CHART_TYPES:
            raise ValueError(f"不支持的图表类型: {self.chart_type}")


class ChartOutput(BaseModel):
    """图表输出"""
    type: str = Field(..., description="图表类型")
    title: str = Field(..., description="图表标题")
    option: Dict[str, Any] = Field(..., description="ECharts option JSON")
    image_base64: Optional[str] = Field(None, description="PNG 图片 base64（可选）")

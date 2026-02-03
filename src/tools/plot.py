"""Tool 定义：plot"""

from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, model_validator
from src.models.plot import PlotSpec, ChartOutput


class PlotInput(BaseModel):
    """生成图表输入"""
    chart_type: str = Field(..., description="图表类型: line, bar, pie, scatter, area")
    title: str = Field(..., description="图表标题")
    x: Optional[str] = Field(None, description="X轴列名")
    y: Optional[str] = Field(None, description="Y轴列名")
    series: Optional[str] = Field(None, description="系列分组列名")
    y_format: Optional[Literal["number", "percent", "currency"]] = Field("number", description="Y轴格式")
    data: Optional[Union[List[Dict[str, Any]], List[List[Any]]]] = Field(None, description="图表数据")
    columns: Optional[List[str]] = Field(None, description="列名（当 data/rows 为二维数组时使用）")
    rows: Optional[List[List[Any]]] = Field(None, description="行数据（可替代 data）")

    @model_validator(mode="after")
    def normalize_data(self):
        data = self.data if self.data is not None else self.rows
        if data is None:
            raise ValueError("必须提供 data 或 rows")

        if data:
            if isinstance(data[0], list):
                if not self.columns:
                    raise ValueError("当 data/rows 为二维数组时必须提供 columns")
                data = [dict(zip(self.columns, row)) for row in data]
        self.data = data
        return self


class PlotOutput(ChartOutput):
    """生成图表输出（继承 ChartOutput）"""
    pass


# Tool 元数据
TOOL_NAME = "plot"
TOOL_DESCRIPTION = """
生成数据可视化图表。

参数：
- chart_type: 图表类型（line, bar, pie, scatter, area）
- title: 图表标题
- x: X轴列名（饼图不需要）
- y: Y轴列名（饼图不需要）
- series: 系列分组列名（可选，用于多系列图表）
- y_format: Y轴格式（number, percent, currency）
- data: 图表数据（List[Dict] 或二维数组）
- columns: 列名（当 data/rows 为二维数组时使用）
- rows: 行数据（可替代 data，来自 run_query 的 rows）

返回：
- type: 图表类型
- title: 图表标题
- option: ECharts option JSON（可直接用于前端渲染）
- image_base64: PNG 图片 base64（可选）

支持的图表类型：
1. line - 折线图（适合趋势分析）
2. bar - 柱状图（适合对比分析）
3. pie - 饼图（适合占比分析）
4. scatter - 散点图（适合相关性分析）
5. area - 面积图（适合趋势对比）

使用场景：
1. 趋势分析：使用折线图展示时间序列
2. 对比分析：使用柱状图对比不同维度
3. 占比分析：使用饼图展示结构占比
"""

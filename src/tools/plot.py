"""Tool 定义：plot"""

from pydantic import BaseModel, Field
from src.models.plot import PlotSpec, ChartOutput


class PlotInput(PlotSpec):
    """生成图表输入（继承 PlotSpec）"""
    pass


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
- data: 图表数据（来自 run_query 的结果）

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

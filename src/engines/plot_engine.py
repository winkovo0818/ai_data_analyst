"""Plot Engine - 图表生成引擎"""

from typing import Dict, Any, List
from src.models.plot import PlotSpec, ChartOutput
from src.utils.logger import log


class PlotEngine:
    """图表生成引擎"""

    def generate(self, spec: PlotSpec) -> ChartOutput:
        """
        生成图表

        Args:
            spec: 图表规范

        Returns:
            ChartOutput: 图表输出
        """
        log.info(f"生成图表: type={spec.chart_type}, title={spec.title}")

        # 根据图表类型生成 ECharts option
        if spec.chart_type == "line":
            option = self._generate_line_chart(spec)
        elif spec.chart_type == "bar":
            option = self._generate_bar_chart(spec)
        elif spec.chart_type == "pie":
            option = self._generate_pie_chart(spec)
        elif spec.chart_type == "scatter":
            option = self._generate_scatter_chart(spec)
        elif spec.chart_type == "area":
            option = self._generate_area_chart(spec)
        else:
            raise ValueError(f"不支持的图表类型: {spec.chart_type}")

        return ChartOutput(
            type=spec.chart_type,
            title=spec.title,
            option=option,
            image_base64=None  # TODO: 可选实现 matplotlib 生成 PNG
        )

    def _generate_line_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成折线图"""
        # 提取数据
        x_data = [row[spec.x] for row in spec.data] if spec.x else []

        # 处理系列
        series_data = {}
        if spec.series:
            # 多系列
            for row in spec.data:
                series_name = str(row[spec.series])
                if series_name not in series_data:
                    series_data[series_name] = []
                series_data[series_name].append(row[spec.y])
        else:
            # 单系列
            series_data["数据"] = [row[spec.y] for row in spec.data]

        # 构建 ECharts option
        option = {
            "title": {"text": spec.title},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": list(series_data.keys())},
            "xAxis": {
                "type": "category",
                "data": x_data,
                "name": spec.x
            },
            "yAxis": {
                "type": "value",
                "name": spec.y,
                "axisLabel": self._get_axis_formatter(spec.y_format)
            },
            "series": [
                {
                    "name": name,
                    "type": "line",
                    "data": values,
                    "smooth": True
                }
                for name, values in series_data.items()
            ]
        }

        return option

    def _generate_bar_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成柱状图"""
        x_data = [row[spec.x] for row in spec.data] if spec.x else []

        series_data = {}
        if spec.series:
            for row in spec.data:
                series_name = str(row[spec.series])
                if series_name not in series_data:
                    series_data[series_name] = []
                series_data[series_name].append(row[spec.y])
        else:
            series_data["数据"] = [row[spec.y] for row in spec.data]

        option = {
            "title": {"text": spec.title},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": list(series_data.keys())},
            "xAxis": {
                "type": "category",
                "data": x_data,
                "name": spec.x
            },
            "yAxis": {
                "type": "value",
                "name": spec.y,
                "axisLabel": self._get_axis_formatter(spec.y_format)
            },
            "series": [
                {
                    "name": name,
                    "type": "bar",
                    "data": values
                }
                for name, values in series_data.items()
            ]
        }

        return option

    def _generate_pie_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成饼图"""
        # 饼图不需要 x/y，使用第一个和第二个字段
        keys = list(spec.data[0].keys())
        name_key = keys[0]
        value_key = keys[1] if len(keys) > 1 else keys[0]

        pie_data = [
            {"name": str(row[name_key]), "value": row[value_key]}
            for row in spec.data
        ]

        option = {
            "title": {"text": spec.title, "left": "center"},
            "tooltip": {"trigger": "item"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [
                {
                    "type": "pie",
                    "radius": "50%",
                    "data": pie_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowOffsetX": 0,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    }
                }
            ]
        }

        return option

    def _generate_scatter_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成散点图"""
        scatter_data = [[row[spec.x], row[spec.y]] for row in spec.data]

        option = {
            "title": {"text": spec.title},
            "tooltip": {"trigger": "item"},
            "xAxis": {"name": spec.x},
            "yAxis": {"name": spec.y},
            "series": [
                {
                    "type": "scatter",
                    "data": scatter_data
                }
            ]
        }

        return option

    def _generate_area_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成面积图"""
        option = self._generate_line_chart(spec)
        # 修改为面积图
        for series in option["series"]:
            series["areaStyle"] = {}
        return option

    def _get_axis_formatter(self, format_type: str) -> Dict[str, Any]:
        """获取坐标轴格式化器"""
        if format_type == "percent":
            return {"formatter": "{value}%"}
        elif format_type == "currency":
            return {"formatter": "${value}"}
        else:
            return {"formatter": "{value}"}


# 全局单例
_plot_engine = None


def get_plot_engine() -> PlotEngine:
    """获取 PlotEngine 单例"""
    global _plot_engine
    if _plot_engine is None:
        _plot_engine = PlotEngine()
    return _plot_engine

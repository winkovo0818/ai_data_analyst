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

        if not spec.data:
            raise ValueError("图表数据为空，无法生成图表")

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

    def _validate_xy(self, spec: PlotSpec) -> None:
        if not spec.x or not spec.y:
            raise ValueError("图表必须提供 x 和 y 字段")

    def _build_series(self, spec: PlotSpec) -> Dict[str, Any]:
        """按 x 轴对齐构建 series 数据"""
        self._validate_xy(spec)

        x_data = []
        x_seen = set()
        series_points: Dict[str, Dict[Any, Any]] = {}

        for row in spec.data:
            if spec.x not in row or spec.y not in row:
                raise ValueError("图表数据缺少必要字段")
            x_val = row[spec.x]
            y_val = row[spec.y]

            if x_val not in x_seen:
                x_seen.add(x_val)
                x_data.append(x_val)

            series_name = "数据"
            if spec.series:
                if spec.series not in row:
                    raise ValueError("图表数据缺少 series 字段")
                series_name = str(row[spec.series])

            if series_name not in series_points:
                series_points[series_name] = {}
            series_points[series_name][x_val] = y_val

        # 对齐到统一的 x 轴
        aligned_series = {}
        for name, points in series_points.items():
            aligned_series[name] = [points.get(x) for x in x_data]

        return {"x_data": x_data, "series": aligned_series}

    def _generate_line_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成折线图"""
        aligned = self._build_series(spec)
        x_data = aligned["x_data"]
        series_data = aligned["series"]

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
        aligned = self._build_series(spec)
        x_data = aligned["x_data"]
        series_data = aligned["series"]

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
        if spec.x and spec.y:
            name_key = spec.x
            value_key = spec.y
        else:
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
        self._validate_xy(spec)
        if any(spec.x not in row or spec.y not in row for row in spec.data):
            raise ValueError("图表数据缺少必要字段")
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

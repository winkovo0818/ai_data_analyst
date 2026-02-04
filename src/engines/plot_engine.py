"""Plot Engine - 图表生成引擎"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
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
        elif spec.chart_type == "heatmap":
            option = self._generate_heatmap_chart(spec)
        elif spec.chart_type == "boxplot":
            option = self._generate_boxplot_chart(spec)
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

    def _is_numeric(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _is_datetime(self, value: Any) -> bool:
        if isinstance(value, (datetime, date)):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return True
            except ValueError:
                return False
        return False

    def _infer_column_type(self, data: List[Dict[str, Any]], col: str) -> str:
        for row in data:
            if col not in row:
                continue
            value = row.get(col)
            if value is None:
                continue
            if self._is_numeric(value):
                return "number"
            if self._is_datetime(value):
                return "datetime"
            return "category"
        return "category"

    def _unique_count(self, data: List[Dict[str, Any]], col: str, limit: int = 50) -> int:
        values = []
        for row in data:
            if col in row and row[col] is not None:
                values.append(row[col])
                if len(values) >= limit:
                    break
        return len(set(values))

    def _collect_numeric_values(self, data: List[Dict[str, Any]], col: str, limit: int = 500) -> List[float]:
        values = []
        for row in data:
            if col in row:
                value = row.get(col)
                if self._is_numeric(value):
                    values.append(float(value))
                    if len(values) >= limit:
                        break
        return values

    def _avg_group_size(self, data: List[Dict[str, Any]], col: str) -> float:
        counts: Dict[Any, int] = {}
        for row in data:
            if col in row:
                key = row[col]
                counts[key] = counts.get(key, 0) + 1
        if not counts:
            return 0
        return sum(counts.values()) / len(counts)

    def _infer_format(self, data: List[Dict[str, Any]], col: Optional[str]) -> str:
        if not col:
            return "number"
        name = col.lower()
        percent_keywords = ["率", "占比", "百分比", "percent", "ratio", "%"]
        currency_keywords = ["金额", "价格", "成本", "收入", "销售额", "利润", "cost", "price", "revenue", "amount", "profit"]
        if any(k in name for k in percent_keywords):
            return "percent"
        if any(k in name for k in currency_keywords):
            return "currency"
        values = self._collect_numeric_values(data, col)
        if values:
            vmin = min(values)
            vmax = max(values)
            if vmin >= 0 and vmax <= 1:
                return "percent"
        return "number"

    def _percentile(self, values: List[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        if len(sorted_vals) == 1:
            return sorted_vals[0]
        k = (len(sorted_vals) - 1) * p
        f = int(k)
        c = min(f + 1, len(sorted_vals) - 1)
        if f == c:
            return sorted_vals[f]
        return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)

    def _box_summary(self, values: List[float]) -> List[float]:
        if not values:
            return [0, 0, 0, 0, 0]
        min_v = min(values)
        max_v = max(values)
        q1 = self._percentile(values, 0.25)
        median = self._percentile(values, 0.5)
        q3 = self._percentile(values, 0.75)
        return [min_v, q1, median, q3, max_v]

    def _base_option(self, title: str) -> Dict[str, Any]:
        return {
            "title": {"text": title, "left": "center"},
            "color": ["#5470C6", "#91CC75", "#FAC858", "#EE6666", "#73C0DE", "#3BA272", "#FC8452", "#9A60B4", "#EA7CCC"],
            "textStyle": {"fontFamily": "PingFang SC, Microsoft YaHei, Arial", "fontSize": 12},
            "grid": {"left": 48, "right": 28, "top": 60, "bottom": 44, "containLabel": True},
            "tooltip": {"confine": True},
            "legend": {"top": 28}
        }

    def recommend(
        self,
        data: List[Dict[str, Any]],
        x: Optional[str] = None,
        y: Optional[str] = None,
        series: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        根据数据推荐图表类型与字段映射
        """
        if not data:
            raise ValueError("图表数据为空，无法推荐图表")

        columns = list(data[0].keys())
        column_types = {col: self._infer_column_type(data, col) for col in columns}

        numeric_cols = [c for c, t in column_types.items() if t == "number"]
        datetime_cols = [c for c, t in column_types.items() if t == "datetime"]
        category_cols = [c for c, t in column_types.items() if t == "category"]

        if y is None:
            if not numeric_cols:
                raise ValueError("无法识别数值列用于 Y 轴")
            y = numeric_cols[0]

        if x is None:
            candidate_datetime = [c for c in datetime_cols if c != y]
            candidate_category = [c for c in category_cols if c != y]
            if candidate_datetime:
                x = candidate_datetime[0]
            elif candidate_category:
                x = candidate_category[0]
            elif len(numeric_cols) > 1:
                x = [c for c in numeric_cols if c != y][0]
            else:
                raise ValueError("无法识别 X 轴字段")

        if series is None:
            candidates = [c for c in category_cols if c not in {x, y}]
            for c in candidates:
                if self._unique_count(data, c) <= 12:
                    series = c
                    break

        y_format = self._infer_format(data, y)

        chart_type = "bar"
        if x in numeric_cols and y in numeric_cols and x != y:
            chart_type = "scatter"
            series = None
        elif x in datetime_cols:
            chart_type = "line"
        else:
            x_unique = self._unique_count(data, x) if x else 0
            series_unique = self._unique_count(data, series) if series else 0
            if series and x in category_cols:
                if x_unique * series_unique >= 60 or series_unique > 8 or x_unique > 20:
                    chart_type = "heatmap"
                else:
                    chart_type = "bar"
            else:
                if x in category_cols:
                    avg_group = self._avg_group_size(data, x)
                    if y in numeric_cols and len(data) >= 80 and x_unique <= 12 and avg_group >= 5:
                        chart_type = "boxplot"
                    elif x_unique <= 8:
                        chart_type = "pie"
                    else:
                        chart_type = "bar"

        if chart_type == "pie":
            series = None
        if chart_type == "heatmap" and not series:
            chart_type = "bar"

        return {
            "chart_type": chart_type,
            "x": x,
            "y": y,
            "series": series,
            "y_format": y_format
        }

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

        option = self._base_option(spec.title)
        option.update({
            "tooltip": {"trigger": "axis", "confine": True},
            "legend": {"data": list(series_data.keys()), "top": 28},
            "xAxis": {
                "type": "category",
                "data": x_data,
                "name": spec.x,
                "axisLabel": {"interval": "auto"}
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
                    "smooth": True,
                    "showSymbol": False
                }
                for name, values in series_data.items()
            ]
        })

        return option

    def _generate_bar_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成柱状图"""
        aligned = self._build_series(spec)
        x_data = aligned["x_data"]
        series_data = aligned["series"]

        option = self._base_option(spec.title)
        option.update({
            "tooltip": {"trigger": "axis", "confine": True},
            "legend": {"data": list(series_data.keys()), "top": 28},
            "xAxis": {
                "type": "category",
                "data": x_data,
                "name": spec.x,
                "axisLabel": {"interval": "auto"}
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
        })

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

        option = self._base_option(spec.title)
        option.update({
            "tooltip": {"trigger": "item", "confine": True},
            "legend": {"orient": "vertical", "left": "left", "top": 48},
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
        })

        return option

    def _generate_scatter_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成散点图"""
        self._validate_xy(spec)
        if any(spec.x not in row or spec.y not in row for row in spec.data):
            raise ValueError("图表数据缺少必要字段")
        scatter_data = [[row[spec.x], row[spec.y]] for row in spec.data]

        option = self._base_option(spec.title)
        option.update({
            "tooltip": {"trigger": "item", "confine": True},
            "xAxis": {"name": spec.x, "type": "value"},
            "yAxis": {"name": spec.y, "type": "value", "axisLabel": self._get_axis_formatter(spec.y_format)},
            "series": [
                {
                    "type": "scatter",
                    "data": scatter_data
                }
            ]
        })

        return option

    def _generate_area_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成面积图"""
        option = self._generate_line_chart(spec)
        # 修改为面积图
        for series in option["series"]:
            series["areaStyle"] = {}
        return option

    def _generate_heatmap_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成热力图"""
        if not spec.x or not spec.y or not spec.series:
            raise ValueError("热力图需要 x, y, series 字段")

        x_values: List[Any] = []
        y_values: List[Any] = []
        x_index: Dict[Any, int] = {}
        y_index: Dict[Any, int] = {}
        heatmap_data: List[List[Any]] = []
        min_val = None
        max_val = None

        for row in spec.data:
            if spec.x not in row or spec.series not in row or spec.y not in row:
                raise ValueError("图表数据缺少必要字段")
            x_val = row[spec.x]
            y_val = row[spec.series]
            value = row[spec.y]

            if x_val not in x_index:
                x_index[x_val] = len(x_values)
                x_values.append(x_val)
            if y_val not in y_index:
                y_index[y_val] = len(y_values)
                y_values.append(y_val)

            heatmap_data.append([x_index[x_val], y_index[y_val], value])

            if self._is_numeric(value):
                min_val = value if min_val is None else min(min_val, value)
                max_val = value if max_val is None else max(max_val, value)

        if min_val is None:
            min_val, max_val = 0, 0

        option = self._base_option(spec.title)
        option.update({
            "tooltip": {"position": "top", "confine": True},
            "grid": {"left": 80, "right": 40, "top": 60, "bottom": 60, "containLabel": True},
            "xAxis": {"type": "category", "data": x_values, "name": spec.x},
            "yAxis": {"type": "category", "data": y_values, "name": spec.series},
            "visualMap": {
                "min": min_val,
                "max": max_val,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": 10
            },
            "series": [
                {
                    "type": "heatmap",
                    "data": heatmap_data,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0, 0, 0, 0.3)"
                        }
                    }
                }
            ]
        })

        return option

    def _generate_boxplot_chart(self, spec: PlotSpec) -> Dict[str, Any]:
        """生成箱线图"""
        if not spec.x or not spec.y:
            raise ValueError("箱线图需要 x, y 字段")

        grouped: Dict[Any, List[float]] = {}
        for row in spec.data:
            if spec.x not in row or spec.y not in row:
                raise ValueError("图表数据缺少必要字段")
            x_val = row[spec.x]
            y_val = row[spec.y]
            if self._is_numeric(y_val):
                grouped.setdefault(x_val, []).append(float(y_val))

        categories = list(grouped.keys())
        box_data = [self._box_summary(grouped[cat]) for cat in categories]

        option = self._base_option(spec.title)
        option.update({
            "tooltip": {"trigger": "item", "confine": True},
            "xAxis": {
                "type": "category",
                "data": categories,
                "name": spec.x,
                "boundaryGap": True,
                "axisLabel": {"interval": "auto", "rotate": 20}
            },
            "yAxis": {
                "type": "value",
                "name": spec.y,
                "axisLabel": self._get_axis_formatter(spec.y_format)
            },
            "series": [
                {
                    "type": "boxplot",
                    "data": box_data
                }
            ]
        })

        return option

    def _get_axis_formatter(self, format_type: str) -> Dict[str, Any]:
        """获取坐标轴格式化器"""
        if format_type == "percent":
            return {"formatter": "{value}%"}
        elif format_type == "currency":
            return {"formatter": "¥{value}"}
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

"""Tool Executor - 工具执行器"""

import time
import copy
from typing import Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from src.tools import TOOL_REGISTRY
from src.engines.dataset_manager import get_dataset_manager
from src.engines.query_engine import get_query_engine, QueryExecutionError
from src.engines.plot_engine import get_plot_engine
from src.models.query import QuerySpec
from src.models.plot import PlotSpec
from src.utils.logger import log
from src.utils.trace import StepLog


class ToolExecutionError(Exception):
    """工具执行错误（结构化）"""

    def __init__(self, code: str, message: str, detail: Dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


class ToolExecutor:
    """工具执行器"""

    def __init__(self):
        self.dataset_manager = get_dataset_manager()
        self.query_engine = get_query_engine()
        self.plot_engine = get_plot_engine()

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            执行结果
        """
        log.info(f"执行工具: {tool_name}")
        start_time = time.time()

        try:
            # 验证工具存在
            if tool_name not in TOOL_REGISTRY:
                raise ValueError(f"未知工具: {tool_name}")

            tool_def = TOOL_REGISTRY[tool_name]
            input_schema = tool_def["input_schema"]
            normalized_args = args
            fixes: Dict[str, Any] = {}

            if tool_name == "run_query":
                normalized_args = self._normalize_run_query_args(args)
                normalized_args, fixes = self._auto_fix_run_query_args(normalized_args)

            # 验证参数
            validated_args = input_schema(**normalized_args)

            # 执行工具
            if tool_name == "create_dataset":
                result = self._execute_create_dataset(validated_args)
            elif tool_name == "get_schema":
                result = self._execute_get_schema(validated_args)
            elif tool_name == "sample_rows":
                result = self._execute_sample_rows(validated_args)
            elif tool_name == "run_query":
                result = self._execute_run_query(validated_args)
            elif tool_name == "plot":
                result = self._execute_plot(validated_args)
            elif tool_name == "resolve_fields":
                result = self._execute_resolve_fields(validated_args)
            else:
                raise ValueError(f"工具未实现: {tool_name}")

            latency = (time.time() - start_time) * 1000
            log.info(f"工具执行成功: {tool_name} ({latency:.2f}ms)")

            return result

        except ValidationError as e:
            latency = (time.time() - start_time) * 1000
            log.error(f"工具执行失败: {tool_name} - {e} ({latency:.2f}ms)")
            raise ToolExecutionError(
                code="VALIDATION_ERROR",
                message="参数校验失败",
                detail={"errors": e.errors(), "fixes": fixes}
            ) from e
        except QueryExecutionError as e:
            latency = (time.time() - start_time) * 1000
            log.error(f"工具执行失败: {tool_name} - {e} ({latency:.2f}ms)")
            raise ToolExecutionError(
                code="SQL_ERROR",
                message=str(e),
                detail={"sql": e.sql, "params": e.params, "cause": e.cause}
            ) from e
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            log.error(f"工具执行失败: {tool_name} - {e} ({latency:.2f}ms)")
            raise ToolExecutionError(
                code="TOOL_ERROR",
                message=str(e),
                detail={"exception": type(e).__name__}
            ) from e

    def _normalize_run_query_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """归一化 run_query 参数"""
        normalized = copy.deepcopy(args)

        def norm_op(value: str) -> str:
            alias = {
                "==": "=", "eq": "=", "neq": "!=", "gt": ">", "gte": ">=",
                "lt": "<", "lte": "<=", "like": "like", "contains": "contains"
            }
            value = value.strip()
            value_lower = value.lower()
            return alias.get(value_lower, value_lower)

        for f in normalized.get("filters", []) or []:
            if isinstance(f.get("op"), str):
                f["op"] = norm_op(f["op"])

        for h in normalized.get("having", []) or []:
            if isinstance(h.get("op"), str):
                h["op"] = norm_op(h["op"])

        for s in normalized.get("sort", []) or []:
            if isinstance(s.get("dir"), str):
                s["dir"] = s["dir"].lower()

        top_k = normalized.get("top_k")
        if top_k and isinstance(top_k.get("order"), str):
            top_k["order"] = top_k["order"].lower()

        time_bucket = normalized.get("time_bucket")
        if time_bucket and isinstance(time_bucket.get("granularity"), str):
            time_bucket["granularity"] = time_bucket["granularity"].lower()

        return normalized

    def _auto_fix_run_query_args(self, args: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """自动修正常见字段错误（保守策略）"""
        dataset_id = args.get("dataset_id")
        if not dataset_id:
            return args, {}

        metadata = self.dataset_manager.get_schema(dataset_id)
        columns = [c.name for c in metadata.columns_schema]
        col_set = set(columns)
        fixes: Dict[str, Any] = {}

        from difflib import SequenceMatcher

        def best_match(name: str) -> str | None:
            if name in col_set:
                return name
            for col in columns:
                if col.lower() == name.lower():
                    return col
            best = None
            best_score = 0.0
            for col in columns:
                score = SequenceMatcher(None, name.lower(), col.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best = col
            if best_score >= 0.85:
                return best
            return None

        def fix_field(container: Dict[str, Any], key: str, path: str):
            value = container.get(key)
            if isinstance(value, str):
                mapped = best_match(value)
                if mapped and mapped != value:
                    container[key] = mapped
                    fixes[path] = {"from": value, "to": mapped}

        for f in args.get("filters", []) or []:
            fix_field(f, "col", "filters.col")

        for h in args.get("having", []) or []:
            fix_field(h, "col", "having.col")

        for agg in args.get("aggregations", []) or []:
            if agg.get("col") != "*":
                fix_field(agg, "col", "aggregations.col")

        for col_index, col in enumerate(args.get("group_by", []) or []):
            mapped = best_match(col)
            if mapped and mapped != col:
                args["group_by"][col_index] = mapped
                fixes[f"group_by[{col_index}]"] = {"from": col, "to": mapped}

        for s in args.get("sort", []) or []:
            fix_field(s, "col", "sort.col")

        top_k = args.get("top_k") or {}
        if top_k:
            fix_field(top_k, "by", "top_k.by")

        time_bucket = args.get("time_bucket") or {}
        if time_bucket:
            fix_field(time_bucket, "col", "time_bucket.col")

        for ratio in args.get("ratios", []) or []:
            fix_field(ratio, "numerator", "ratios.numerator")
            fix_field(ratio, "denominator", "ratios.denominator")

        return args, fixes

    def _execute_create_dataset(self, args: Any) -> Dict[str, Any]:
        """执行 create_dataset"""
        # 注意：这里假设文件已经上传，file_id 对应实际文件路径
        # 实际实现中需要从文件上传服务获取文件路径
        from src.core.config import settings

        # 简化实现：假设 file_id 就是文件名
        file_path = settings.upload_dir / args.file_id

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        metadata = self.dataset_manager.create_dataset(
            file_id=args.file_id,
            file_path=file_path,
            original_filename=args.file_id,
            sheet=args.sheet,
            header_row=args.header_row
        )

        return {
            "dataset_id": metadata.dataset_id,
            "row_count": metadata.row_count,
            "column_count": metadata.column_count
        }

    def _execute_get_schema(self, args: Any) -> Dict[str, Any]:
        """执行 get_schema"""
        metadata = self.dataset_manager.get_schema(args.dataset_id)

        return {
            "dataset_id": metadata.dataset_id,
            "columns": [col.model_dump() for col in metadata.columns_schema],  # 使用新字段名
            "row_count": metadata.row_count
        }

    def _execute_sample_rows(self, args: Any) -> Dict[str, Any]:
        """执行 sample_rows"""
        sample = self.dataset_manager.sample_rows(
            dataset_id=args.dataset_id,
            n=args.n,
            columns=args.columns
        )

        return sample.model_dump()

    def _execute_run_query(self, args: Any) -> Dict[str, Any]:
        """执行 run_query"""
        # args 已经是 QuerySpec 实例
        result = self.query_engine.execute(args)
        return result.model_dump()

    def _execute_plot(self, args: Any) -> Dict[str, Any]:
        """执行 plot"""
        # args 已经过 PlotInput 规范化
        payload = args.model_dump(exclude_none=True, exclude={"rows", "columns"})
        chart_type = payload.get("chart_type")
        x = payload.get("x")
        y = payload.get("y")
        series = payload.get("series")

        if payload.get("y_format") in (None, "auto") and x and y and chart_type not in (None, "auto"):
            recommendation = self.plot_engine.recommend(
                payload.get("data", []),
                x=x,
                y=y,
                series=series
            )
            payload["y_format"] = recommendation.get("y_format", payload.get("y_format"))
            if series is None:
                payload["series"] = recommendation.get("series")

        if chart_type in (None, "auto") or not x or not y:
            recommendation = self.plot_engine.recommend(
                payload.get("data", []),
                x=x,
                y=y,
                series=series
            )
            if chart_type in (None, "auto"):
                payload["chart_type"] = recommendation["chart_type"]
            if not x:
                payload["x"] = recommendation.get("x")
            if not y:
                payload["y"] = recommendation.get("y")
            if series is None:
                payload["series"] = recommendation.get("series")
            if payload.get("y_format") in (None, "auto"):
                payload["y_format"] = recommendation.get("y_format", payload.get("y_format"))

        spec = PlotSpec(**payload)
        chart = self.plot_engine.generate(spec)
        return chart.model_dump()

    def _execute_resolve_fields(self, args: Any) -> Dict[str, Any]:
        """执行 resolve_fields"""
        # 基于相似度与包含关系的字段映射
        metadata = self.dataset_manager.get_schema(args.dataset_id)
        from difflib import SequenceMatcher
        import re

        def normalize(text: str) -> str:
            return re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5]+", "", text).lower()

        mapped_columns = []
        suggestions: Dict[str, list] = {}

        for term in args.terms:
            term_norm = normalize(term)
            scored = []
            for col in metadata.columns_schema:  # 使用新字段名
                col_norm = normalize(col.name)
                score = SequenceMatcher(None, term_norm, col_norm).ratio()
                if term_norm and (term_norm in col_norm or col_norm in term_norm):
                    score = min(1.0, score + 0.2)
                scored.append((col.name, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            suggestions[term] = [name for name, _ in scored[:5]]

            if scored and scored[0][1] >= 0.65:
                if scored[0][0] not in mapped_columns:
                    mapped_columns.append(scored[0][0])

        return {
            "mapped_columns": mapped_columns,
            "suggestions": suggestions
        }


# 全局单例
_tool_executor = None


def get_tool_executor() -> ToolExecutor:
    """获取 ToolExecutor 单例"""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor

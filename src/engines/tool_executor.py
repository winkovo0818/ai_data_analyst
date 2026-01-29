"""Tool Executor - 工具执行器"""

import time
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

from src.tools import TOOL_REGISTRY
from src.engines.dataset_manager import get_dataset_manager
from src.engines.query_engine import get_query_engine
from src.engines.plot_engine import get_plot_engine
from src.models.query import QuerySpec
from src.models.plot import PlotSpec
from src.utils.logger import log
from src.utils.trace import StepLog


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

            # 验证参数
            tool_def = TOOL_REGISTRY[tool_name]
            input_schema = tool_def["input_schema"]
            validated_args = input_schema(**args)

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

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            log.error(f"工具执行失败: {tool_name} - {e} ({latency:.2f}ms)")
            raise

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
        # args 已经是 PlotSpec 实例
        chart = self.plot_engine.generate(args)
        return chart.model_dump()

    def _execute_resolve_fields(self, args: Any) -> Dict[str, Any]:
        """执行 resolve_fields"""
        # 简单实现：基于关键词匹配列名
        metadata = self.dataset_manager.get_schema(args.dataset_id)

        mapped_columns = []
        for term in args.terms:
            term_lower = term.lower()
            for col in metadata.columns_schema:  # 使用新字段名
                if term_lower in col.name.lower() or col.name.lower() in term_lower:
                    if col.name not in mapped_columns:
                        mapped_columns.append(col.name)

        return {
            "mapped_columns": mapped_columns,
            "suggestions": {term: mapped_columns for term in args.terms}
        }


# 全局单例
_tool_executor = None


def get_tool_executor() -> ToolExecutor:
    """获取 ToolExecutor 单例"""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor

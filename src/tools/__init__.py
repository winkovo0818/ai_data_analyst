"""工具包注册"""

from typing import Dict, Any, Callable
from src.tools.create_dataset import (
    CreateDatasetInput,
    CreateDatasetOutput,
    TOOL_NAME as CREATE_DATASET_NAME,
    TOOL_DESCRIPTION as CREATE_DATASET_DESC
)
from src.tools.get_schema import (
    GetSchemaInput,
    GetSchemaOutput,
    TOOL_NAME as GET_SCHEMA_NAME,
    TOOL_DESCRIPTION as GET_SCHEMA_DESC
)
from src.tools.sample_rows import (
    SampleRowsInput,
    SampleRowsOutput,
    TOOL_NAME as SAMPLE_ROWS_NAME,
    TOOL_DESCRIPTION as SAMPLE_ROWS_DESC
)
from src.tools.run_query import (
    RunQueryInput,
    RunQueryOutput,
    TOOL_NAME as RUN_QUERY_NAME,
    TOOL_DESCRIPTION as RUN_QUERY_DESC
)
from src.tools.plot import (
    PlotInput,
    PlotOutput,
    TOOL_NAME as PLOT_NAME,
    TOOL_DESCRIPTION as PLOT_DESC
)
from src.tools.resolve_fields import (
    ResolveFieldsInput,
    ResolveFieldsOutput,
    TOOL_NAME as RESOLVE_FIELDS_NAME,
    TOOL_DESCRIPTION as RESOLVE_FIELDS_DESC
)


# 工具注册表
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    CREATE_DATASET_NAME: {
        "name": CREATE_DATASET_NAME,
        "description": CREATE_DATASET_DESC,
        "input_schema": CreateDatasetInput,
        "output_schema": CreateDatasetOutput,
    },
    GET_SCHEMA_NAME: {
        "name": GET_SCHEMA_NAME,
        "description": GET_SCHEMA_DESC,
        "input_schema": GetSchemaInput,
        "output_schema": GetSchemaOutput,
    },
    SAMPLE_ROWS_NAME: {
        "name": SAMPLE_ROWS_NAME,
        "description": SAMPLE_ROWS_DESC,
        "input_schema": SampleRowsInput,
        "output_schema": SampleRowsOutput,
    },
    RUN_QUERY_NAME: {
        "name": RUN_QUERY_NAME,
        "description": RUN_QUERY_DESC,
        "input_schema": RunQueryInput,
        "output_schema": RunQueryOutput,
    },
    PLOT_NAME: {
        "name": PLOT_NAME,
        "description": PLOT_DESC,
        "input_schema": PlotInput,
        "output_schema": PlotOutput,
    },
    RESOLVE_FIELDS_NAME: {
        "name": RESOLVE_FIELDS_NAME,
        "description": RESOLVE_FIELDS_DESC,
        "input_schema": ResolveFieldsInput,
        "output_schema": ResolveFieldsOutput,
    },
}


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """获取工具的 JSON Schema（用于 LLM）"""
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"未知工具: {tool_name}")

    tool = TOOL_REGISTRY[tool_name]
    return {
        "name": tool["name"],
        "description": tool["description"],
        "parameters": tool["input_schema"].model_json_schema()
    }


def get_all_tool_schemas() -> list[Dict[str, Any]]:
    """获取所有工具的 Schema"""
    return [get_tool_schema(name) for name in TOOL_REGISTRY.keys()]


__all__ = [
    "TOOL_REGISTRY",
    "get_tool_schema",
    "get_all_tool_schemas",
    # Tool Names
    "CREATE_DATASET_NAME",
    "GET_SCHEMA_NAME",
    "SAMPLE_ROWS_NAME",
    "RUN_QUERY_NAME",
    "PLOT_NAME",
    "RESOLVE_FIELDS_NAME",
]

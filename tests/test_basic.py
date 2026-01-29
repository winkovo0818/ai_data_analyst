"""基础测试"""

import pytest
from pathlib import Path
from src.core.config import settings
from src.models.query import FilterCondition, Aggregation, QuerySpec


def test_settings():
    """测试配置加载"""
    assert settings is not None
    assert settings.max_tool_steps == 8
    assert settings.max_query_rows == 10000


def test_filter_condition():
    """测试过滤条件模型"""
    filter = FilterCondition(
        col="age",
        op=">=",
        value=18
    )
    assert filter.col == "age"
    assert filter.op == ">="
    assert filter.value == 18


def test_aggregation():
    """测试聚合模型"""
    agg = Aggregation(
        **{"as": "total", "agg": "sum", "col": "amount"}
    )
    assert agg.as_ == "total"
    assert agg.agg == "sum"
    assert agg.col == "amount"


def test_query_spec():
    """测试查询规范"""
    spec = QuerySpec(
        dataset_id="ds_test",
        filters=[
            FilterCondition(col="status", op="=", value="active")
        ],
        group_by=["category"],
        aggregations=[
            Aggregation(**{"as": "count", "agg": "count", "col": "*"})
        ],
        limit=100
    )

    assert spec.dataset_id == "ds_test"
    assert len(spec.filters) == 1
    assert len(spec.group_by) == 1
    assert len(spec.aggregations) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

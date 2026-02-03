"""系统常量定义"""

from typing import Set

# 支持的文件类型
SUPPORTED_FILE_EXTENSIONS: Set[str] = {".xlsx", ".xls", ".csv"}

# QuerySpec 操作符白名单
ALLOWED_FILTER_OPERATORS: Set[str] = {
    "=", "!=", ">", ">=", "<", "<=",
    "in", "between", "contains", "is_null"
}

# 聚合函数白名单
ALLOWED_AGGREGATIONS: Set[str] = {
    "sum", "avg", "min", "max", "count", "nunique"
}

# 衍生字段表达式白名单（允许的函数和操作符）
ALLOWED_EXPR_FUNCTIONS: Set[str] = {
    "nullif", "coalesce", "round", "abs",
    "+", "-", "*", "/"
}

# 时间分桶粒度
TIME_BUCKET_GRAINULARITIES: Set[str] = {
    "hour", "day", "week", "month", "quarter", "year"
}

# 图表类型
CHART_TYPES: Set[str] = {
    "line", "bar", "pie", "scatter", "area"
}

# 数据类型映射
DTYPE_MAPPING = {
    "int64": "int",
    "float64": "float",
    "object": "string",
    "bool": "boolean",
    "datetime64[ns]": "datetime"
}

# 最大限制
MAX_COLUMNS = 500
MAX_ROWS_SAMPLE = 1000
MAX_CHART_SERIES = 20

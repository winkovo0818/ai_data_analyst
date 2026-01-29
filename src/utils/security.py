"""安全防护工具"""

import re
from typing import Any, Dict
from src.utils.logger import log


class SecurityValidator:
    """安全校验器"""

    # SQL 注入关键词黑名单
    SQL_INJECTION_KEYWORDS = [
        "drop", "delete", "truncate", "insert", "update",
        "exec", "execute", "script", "javascript",
        "--", ";--", "/*", "*/", "xp_", "sp_"
    ]

    # Prompt 注入检测关键词
    PROMPT_INJECTION_KEYWORDS = [
        "ignore previous", "ignore all", "new instruction",
        "system:", "assistant:", "you are now",
        "disregard", "forget everything"
    ]

    @classmethod
    def validate_column_name(cls, col_name: str) -> bool:
        """
        验证列名安全性

        Args:
            col_name: 列名

        Returns:
            是否安全
        """
        # 只允许字母、数字、下划线、中文
        pattern = r'^[\w\u4e00-\u9fa5]+$'
        if not re.match(pattern, col_name):
            log.warning(f"不安全的列名: {col_name}")
            return False
        return True

    @classmethod
    def validate_expression(cls, expr: str) -> bool:
        """
        验证表达式安全性

        Args:
            expr: 表达式

        Returns:
            是否安全
        """
        expr_lower = expr.lower()

        # 检查 SQL 注入
        for keyword in cls.SQL_INJECTION_KEYWORDS:
            if keyword in expr_lower:
                log.warning(f"表达式包含危险关键词: {keyword}")
                return False

        return True

    @classmethod
    def sanitize_string_value(cls, value: str) -> str:
        """
        清理字符串值（防止注入）

        Args:
            value: 原始值

        Returns:
            清理后的值
        """
        # 转义单引号
        return value.replace("'", "''")

    @classmethod
    def detect_prompt_injection(cls, user_input: str) -> bool:
        """
        检测 Prompt 注入

        Args:
            user_input: 用户输入

        Returns:
            是否检测到注入
        """
        input_lower = user_input.lower()

        for keyword in cls.PROMPT_INJECTION_KEYWORDS:
            if keyword in input_lower:
                log.warning(f"检测到 Prompt 注入尝试: {keyword}")
                return True

        return False

    @classmethod
    def validate_query_complexity(cls, query_spec: Dict[str, Any]) -> bool:
        """
        验证查询复杂度

        Args:
            query_spec: 查询规范

        Returns:
            是否在允许范围内
        """
        # 检查过滤条件数量
        if len(query_spec.get("filters", [])) > 20:
            log.warning("过滤条件过多")
            return False

        # 检查分组列数量
        if len(query_spec.get("group_by", [])) > 10:
            log.warning("分组列过多")
            return False

        # 检查聚合数量
        if len(query_spec.get("aggregations", [])) > 20:
            log.warning("聚合操作过多")
            return False

        return True

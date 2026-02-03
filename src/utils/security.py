"""安全防护工具"""

import re
from typing import Any, Dict, Callable, List, Tuple, Set, Optional
from src.utils.logger import log
from src.core.constants import ALLOWED_EXPR_FUNCTIONS


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

        # 检查 having 条件数量
        if len(query_spec.get("having", [])) > 20:
            log.warning("having 条件过多")
            return False

        # 检查比例指标数量
        if len(query_spec.get("ratios", [])) > 20:
            log.warning("比例指标过多")
            return False

        return True

    @classmethod
    def parse_expression(
        cls,
        expr: str,
        allowed_identifiers: Set[str],
        quote_identifier: Callable[[str], str]
    ) -> str:
        """
        安全解析表达式并输出 SQL 片段

        Args:
            expr: 原始表达式
            allowed_identifiers: 允许的字段/别名集合
            quote_identifier: 标识符引用函数

        Returns:
            规范化后的安全表达式
        """
        if not cls.validate_expression(expr):
            raise ValueError("表达式包含非法内容")

        token_spec = re.compile(
            r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_\u4e00-\u9fa5][\w\u4e00-\u9fa5]*)|([+\-*/(),]))"
        )

        tokens: List[Tuple[str, str]] = []
        pos = 0
        while pos < len(expr):
            match = token_spec.match(expr, pos)
            if not match:
                raise ValueError("表达式包含非法字符")
            number, ident, op = match.groups()
            if number:
                tokens.append(("number", number))
            elif ident:
                tokens.append(("ident", ident))
            elif op:
                tokens.append(("op", op))
            pos = match.end()

        index = 0

        def peek() -> Optional[Tuple[str, str]]:
            return tokens[index] if index < len(tokens) else None

        def consume(expected: str | None = None) -> Tuple[str, str]:
            nonlocal index
            if index >= len(tokens):
                raise ValueError("表达式不完整")
            token = tokens[index]
            if expected and token[1] != expected:
                raise ValueError("表达式语法错误")
            index += 1
            return token

        def parse_expression() -> str:
            node = parse_term()
            while True:
                token = peek()
                if token and token[0] == "op" and token[1] in {"+", "-"}:
                    op = consume()[1]
                    right = parse_term()
                    node = f"({node} {op} {right})"
                else:
                    break
            return node

        def parse_term() -> str:
            node = parse_factor()
            while True:
                token = peek()
                if token and token[0] == "op" and token[1] in {"*", "/"}:
                    op = consume()[1]
                    right = parse_factor()
                    node = f"({node} {op} {right})"
                else:
                    break
            return node

        def parse_factor() -> str:
            token = peek()
            if not token:
                raise ValueError("表达式不完整")

            if token[0] == "op" and token[1] in {"+", "-"}:
                op = consume()[1]
                value = parse_factor()
                return f"{op}{value}"

            if token[0] == "number":
                return consume()[1]

            if token[0] == "ident":
                ident = consume()[1]
                next_token = peek()
                if next_token and next_token[0] == "op" and next_token[1] == "(":
                    if ident.lower() not in ALLOWED_EXPR_FUNCTIONS:
                        raise ValueError(f"表达式包含未授权函数: {ident}")
                    consume("(")
                    args: List[str] = []
                    if peek() and not (peek()[0] == "op" and peek()[1] == ")"):
                        args.append(parse_expression())
                        while peek() and peek()[0] == "op" and peek()[1] == ",":
                            consume(",")
                            args.append(parse_expression())
                    consume(")")
                    return f"{ident}({', '.join(args)})"

                if ident not in allowed_identifiers:
                    raise ValueError(f"表达式包含未授权字段: {ident}")
                return quote_identifier(ident)

            if token[0] == "op" and token[1] == "(":
                consume("(")
                inner = parse_expression()
                consume(")")
                return f"({inner})"

            raise ValueError("表达式语法错误")

        result = parse_expression()
        if index != len(tokens):
            raise ValueError("表达式语法错误")
        return result

"""LLM Agent - Tool Calling 循环（正确版本）"""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from openai import APIError as OpenAIAPIError, BadRequestError as OpenAIBadRequestError
from anthropic import APIError as AnthropicAPIError, BadRequestError as AnthropicBadRequestError

from src.core.config import settings
from src.engines.tool_executor import get_tool_executor, ToolExecutionError
from src.utils.logger import log
from src.utils.trace import TraceContext, StepLog


# System Prompt
SYSTEM_PROMPT = """你是一个数据分析规划助手。

你的任务是帮助用户分析结构化数据（Excel/CSV），并回答用户的问题。

重要规则：
1. 你不能直接计算数据，不能编造数据
2. 你必须先调用 get_schema 工具了解数据结构
3. 所有计算必须通过 run_query 工具完成
4. 所有结论必须基于工具返回的结果
5. 不要猜测，必须使用工具获取真实数据
6. 当用户需要图表或可视化时，必须调用 plot 工具生成图表
7. 如果用户提到的字段名与数据集字段不完全匹配，使用 resolve_fields 工具进行语义映射
8. 回答中不要使用 emoji 表情符号，保持专业简洁

工作流程：
1. 先调用 get_schema 了解数据集的字段结构
2. 如果用户提到的字段名不明确，调用 resolve_fields 进行字段映射
3. 然后调用 run_query 进行数据查询和计算
4. 如果用户需要图表，调用 plot 工具生成可视化
5. 基于查询结果给出答案

注意：
- 必须调用工具，不要凭空回答
- run_query 的 aggregations 参数是列表，每个元素包含 as, agg, col 三个字段
- plot 工具需要传入 run_query 返回的数据（推荐 rows + columns）
- resolve_fields 可以帮助你找到用户意图对应的真实字段名
"""


class LLMAgent:
    """LLM Agent"""

    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        self.tool_executor = get_tool_executor()
        self.max_steps = settings.max_tool_steps
        self.llm = self._create_llm(llm_config)

        # 创建工具
        self.tools = self._create_tools()

        # 调试：打印工具信息
        log.info(f"创建了 {len(self.tools)} 个工具:")
        for t in self.tools:
            log.info(f"  - {t.name}: {t.description[:50]}...")

        # 绑定工具并验证
        try:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            log.info("工具已绑定到 LLM")

            # 打印绑定后的工具信息（用于调试）
            if hasattr(self.llm_with_tools, 'kwargs') and 'tools' in self.llm_with_tools.kwargs:
                log.info(f"绑定的工具格式: {json.dumps(self.llm_with_tools.kwargs['tools'], ensure_ascii=False, indent=2)}")
        except Exception as e:
            log.error(f"绑定工具失败: {e}")
            raise

    def _parse_api_error(self, error: Exception, provider: str) -> str:
        """解析 API 错误信息，提取用户友好的错误消息"""
        error_str = str(error)

        # 尝试解析 JSON 错误信息
        try:
            # 匹配 JSON 格式的错误
            json_match = re.search(r"\{.*\}", error_str, re.DOTALL)
            if json_match:
                error_json = json.loads(json_match.group())
                if 'error' in error_json:
                    err = error_json['error']
                    code = err.get('code', 'unknown')
                    message = err.get('message', str(error))
                    error_type = err.get('type', '')

                    # 内容过滤错误
                    if code == 400 and 'content_filter' in error_type:
                        return f"请求被内容安全过滤器拒绝: {message}"
                    elif 'rate_limit' in error_type.lower():
                        return f"API 请求频率超限，请稍后重试"
                    elif 'invalid_api_key' in error_type.lower():
                        return f"{provider} API Key 无效"
                    elif 'insufficient_quota' in error_type.lower():
                        return f"{provider} API 额度不足"
                    else:
                        return f"{provider} API 错误 ({code}): {message}"
        except (json.JSONDecodeError, KeyError):
            pass

        # 常见错误模式匹配
        if 'content_filter' in error_str.lower() or 'high risk' in error_str.lower():
            return "请求被内容安全过滤器拒绝，请尝试修改问题描述"
        elif 'rate limit' in error_str.lower():
            return "API 请求频率超限，请稍后重试"
        elif 'invalid api key' in error_str.lower() or 'authentication' in error_str.lower():
            return f"{provider} API Key 无效或未配置"
        elif 'quota' in error_str.lower() or 'billing' in error_str.lower():
            return f"{provider} API 额度不足，请检查账户余额"
        elif 'timeout' in error_str.lower():
            return "API 请求超时，请重试"
        elif 'connection' in error_str.lower():
            return "无法连接到 API 服务，请检查网络"

        return f"{provider} API 错误: {error_str[:200]}"

    def _create_llm(self, config: Optional[Dict[str, Any]] = None):
        """创建 LLM 实例"""
        provider = config.get("provider") if config else settings.default_llm_provider
        api_key = config.get("api_key") if config else None
        model = config.get("model") if config else settings.default_model
        base_url = config.get("base_url") if config else None

        if not api_key:
            if provider == "openai":
                api_key = settings.openai_api_key
            elif provider == "anthropic":
                api_key = settings.anthropic_api_key

        if not api_key:
            raise ValueError(f"未配置 {provider} 的 API Key")

        log.info(f"初始化 LLM: provider={provider}, model={model}, base_url={base_url}")

        if provider == "openai":
            llm_kwargs = {
                "model": model,
                "api_key": api_key,
                "temperature": 0,
                "model_kwargs": {
                    # 确保启用 function calling
                    "parallel_tool_calls": True,
                }
            }
            if base_url:
                llm_kwargs["base_url"] = base_url

            llm = ChatOpenAI(**llm_kwargs)

            # 验证模型是否支持工具调用
            try:
                test_tools = [{"type": "function", "function": {"name": "test", "description": "test", "parameters": {"type": "object", "properties": {}}}}]
                llm.bind_tools(test_tools)
                log.info("模型支持工具调用")
            except Exception as e:
                log.warning(f"模型可能不支持工具调用: {e}")

            return llm
        elif provider == "anthropic":
            llm_kwargs = {
                "model": model,
                "api_key": api_key,
                "temperature": 0
            }
            if base_url:
                llm_kwargs["base_url"] = base_url
            return ChatAnthropic(**llm_kwargs)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")

    def _create_tools(self):
        """创建工具列表"""
        tool_executor = self.tool_executor

        @tool
        def get_schema(dataset_id: str) -> dict:
            """获取数据集的字段结构和统计信息

            Args:
                dataset_id: 数据集ID

            Returns:
                包含字段信息的字典
            """
            return tool_executor.execute("get_schema", {"dataset_id": dataset_id})

        @tool
        def sample_rows(dataset_id: str, n: int = 5) -> dict:
            """获取数据集的样本行

            Args:
                dataset_id: 数据集ID
                n: 返回行数，默认5行

            Returns:
                样本数据
            """
            return tool_executor.execute("sample_rows", {
                "dataset_id": dataset_id,
                "n": n,
                "columns": None
            })

        @tool
        def run_query(
            dataset_id: str,
            group_by: List[str] = None,
            aggregations: List[dict] = None,
            filters: List[dict] = None,
            derived: List[dict] = None,
            ratios: List[dict] = None,
            time_bucket: dict = None,
            having: List[dict] = None,
            top_k: dict = None,
            sort: List[dict] = None,
            limit: int = 5000
        ) -> dict:
            """执行数据查询和聚合

            Args:
                dataset_id: 数据集ID
                group_by: 分组列名列表，例如 ["账号", "月份"]
                aggregations: 聚合操作列表，每个包含 as, agg, col 三个字段
                    例如: [{"as": "退货总数", "agg": "sum", "col": "退货数量"}]
                    支持的聚合函数: sum, avg, min, max, count, nunique
                filters: 过滤条件列表，每个包含 col, op, value
                    例如: [{"col": "年份", "op": "=", "value": 2025}]
                derived: 衍生字段列表，每个包含 as, expr
                    例如: [{"as": "质量率", "expr": "quality_cnt / nullif(return_qty, 0)"}]
                ratios: 比例/百分比指标列表（可选）
                    例如: [{"as": "退货率", "numerator": "退货数量", "denominator": "销售数量", "kind": "percent"}]
                time_bucket: 时间分桶（可选），包含 col, granularity, as
                having: 聚合后过滤条件（可选），包含 col, op, value
                top_k: Top K 规则（可选），包含 by, k, order
                sort: 排序规则列表，每个包含 col, dir
                    例如: [{"col": "退货总数", "dir": "desc"}]
                limit: 返回行数限制

            Returns:
                查询结果，包含 columns 和 rows
            """
            return tool_executor.execute("run_query", {
                "dataset_id": dataset_id,
                "filters": filters or [],
                "group_by": group_by or [],
                "aggregations": aggregations or [],
                "derived": derived or [],
                "ratios": ratios or [],
                "time_bucket": time_bucket,
                "having": having or [],
                "top_k": top_k,
                "sort": sort or [],
                "limit": limit
            })

        @tool
        def plot(
            chart_type: str,
            title: str,
            data: List[dict] = None,
            columns: List[str] = None,
            rows: List[list] = None,
            x: str = None,
            y: str = None,
            series: str = None,
            y_format: str = "number"
        ) -> dict:
            """生成数据可视化图表

            Args:
                chart_type: 图表类型，支持 line(折线图), bar(柱状图), pie(饼图), scatter(散点图), area(面积图)
                title: 图表标题
                data: 图表数据（List[Dict] 或二维数组）
                columns: 列名（当 data/rows 为二维数组时使用）
                rows: 行数据（可替代 data，来自 run_query 的 rows）
                x: X轴列名（饼图不需要）
                y: Y轴列名（饼图不需要）
                series: 系列分组列名（可选，用于多系列图表）
                y_format: Y轴格式，支持 number, percent, currency

            Returns:
                包含 ECharts option 的图表配置
            """
            return tool_executor.execute("plot", {
                "chart_type": chart_type,
                "title": title,
                "data": data,
                "columns": columns,
                "rows": rows,
                "x": x,
                "y": y,
                "series": series,
                "y_format": y_format
            })

        @tool
        def resolve_fields(dataset_id: str, terms: List[str]) -> dict:
            """将用户提到的字段名映射到数据集中的真实字段名

            当用户提到的字段名与数据集字段不完全匹配时使用此工具。
            例如用户说"退货原因"，但数据集中可能是"产品质量"、"物流异常"等具体字段。

            Args:
                dataset_id: 数据集ID
                terms: 用户提到的字段名或术语列表，例如 ["退货原因", "质量问题"]

            Returns:
                mapped_columns: 匹配到的真实字段名列表
                suggestions: 每个术语对应的建议字段
            """
            return tool_executor.execute("resolve_fields", {
                "dataset_id": dataset_id,
                "terms": terms
            })

        return [get_schema, sample_rows, run_query, plot, resolve_fields]

    def run(self, user_query: str, dataset_id: Optional[str] = None, llm_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """运行 Tool Calling 循环"""
        if llm_config:
            self.llm = self._create_llm(llm_config)
            self.tools = self._create_tools()
            self.llm_with_tools = self.llm.bind_tools(self.tools)

        trace = TraceContext()
        log.info(f"开始分析: trace_id={trace.trace_id}")

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"数据集ID: {dataset_id}\n\n用户问题: {user_query}" if dataset_id else user_query)
        ]

        for step in range(self.max_steps):
            log.info(f"执行步骤 {step + 1}/{self.max_steps}")

            # 调试：打印请求的消息
            log.info(f"发送消息数量: {len(messages)}")
            if messages:
                last_msg = messages[-1]
                log.info(f"最后一条消息类型: {type(last_msg).__name__}")

            try:
                response = self.llm_with_tools.invoke(messages)
            except (OpenAIBadRequestError, OpenAIAPIError) as e:
                error_msg = self._parse_api_error(e, "OpenAI")
                error_code = "LLM_BAD_REQUEST" if isinstance(e, OpenAIBadRequestError) else "LLM_API_ERROR"
                log.error(f"OpenAI API 错误: {error_msg}")
                return {
                    "answer": None,
                    "charts": [],
                    "tables": [],
                    "trace": trace.to_dict(),
                    "steps": step + 1,
                    "error": error_msg,
                    "error_code": error_code,
                    "error_detail": {"provider": "OpenAI", "exception": type(e).__name__}
                }
            except (AnthropicBadRequestError, AnthropicAPIError) as e:
                error_msg = self._parse_api_error(e, "Anthropic")
                error_code = "LLM_BAD_REQUEST" if isinstance(e, AnthropicBadRequestError) else "LLM_API_ERROR"
                log.error(f"Anthropic API 错误: {error_msg}")
                return {
                    "answer": None,
                    "charts": [],
                    "tables": [],
                    "trace": trace.to_dict(),
                    "steps": step + 1,
                    "error": error_msg,
                    "error_code": error_code,
                    "error_detail": {"provider": "Anthropic", "exception": type(e).__name__}
                }
            except Exception as e:
                error_msg = f"LLM 调用失败: {str(e)}"
                log.error(error_msg)
                return {
                    "answer": None,
                    "charts": [],
                    "tables": [],
                    "trace": trace.to_dict(),
                    "steps": step + 1,
                    "error": error_msg,
                    "error_code": "LLM_CALL_FAILED",
                    "error_detail": {"exception": type(e).__name__}
                }

            # 提取 token 使用量
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                # OpenAI 格式
                if 'token_usage' in metadata:
                    usage = metadata['token_usage']
                    trace.llm_tokens += usage.get('total_tokens', 0)
                    # 估算成本 (GPT-4 Turbo 价格: $10/1M input, $30/1M output)
                    input_cost = usage.get('prompt_tokens', 0) * 0.00001
                    output_cost = usage.get('completion_tokens', 0) * 0.00003
                    trace.llm_cost_usd += input_cost + output_cost
                # Anthropic 格式
                elif 'usage' in metadata:
                    usage = metadata['usage']
                    trace.llm_tokens += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                    # Claude 价格: $3/1M input, $15/1M output
                    input_cost = usage.get('input_tokens', 0) * 0.000003
                    output_cost = usage.get('output_tokens', 0) * 0.000015
                    trace.llm_cost_usd += input_cost + output_cost

            # 调试：打印响应信息
            log.info(f"LLM 响应类型: {type(response)}")
            log.info(f"LLM 是否有 tool_calls: {hasattr(response, 'tool_calls')}")
            if hasattr(response, 'tool_calls'):
                log.info(f"tool_calls 内容: {response.tool_calls}")
                log.info(f"tool_calls 数量: {len(response.tool_calls) if response.tool_calls else 0}")
            log.info(f"响应内容前100字: {response.content[:100] if response.content else 'None'}")

            # 打印响应的原始属性（用于深度调试）
            if hasattr(response, 'additional_kwargs'):
                log.info(f"additional_kwargs: {response.additional_kwargs}")
            if hasattr(response, 'response_metadata'):
                log.info(f"response_metadata: {response.response_metadata}")

            if not response.tool_calls:
                final_answer = response.content
                log.info("LLM 给出最终答案")

                # 从 trace 中提取图表和表格
                charts = []
                tables = []
                table_index = 0
                for step_log in trace.steps:
                    if step_log.tool == "plot" and step_log.result:
                        charts.append(step_log.result)
                    elif step_log.tool == "run_query" and step_log.result:
                        table_index += 1
                        tables.append({
                            "name": f"查询结果_{table_index}",
                            "columns": step_log.result.get("columns", []),
                            "rows": step_log.result.get("rows", [])
                        })

                return {
                    "answer": final_answer,
                    "charts": charts,
                    "tables": tables,
                    "trace": trace.to_dict(),
                    "steps": step + 1
                }

            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                step_log = StepLog(
                    tool=tool_name,
                    args=tool_args,
                    timestamp=datetime.now()
                )

                try:
                    import time
                    start = time.time()
                    result = self.tool_executor.execute(tool_name, tool_args)
                    step_log.latency_ms = (time.time() - start) * 1000
                    step_log.result = result

                    messages.append(
                        ToolMessage(
                            content=json.dumps(result, ensure_ascii=False),
                            tool_call_id=tool_call["id"]
                        )
                    )

                    log.info(f"工具执行成功: {tool_name}")

                except ToolExecutionError as e:
                    step_log.error = str(e)
                    step_log.error_code = e.code
                    step_log.error_detail = e.detail
                    log.error(f"工具执行失败: {tool_name} - {e}")

                    messages.append(
                        ToolMessage(
                            content=json.dumps(
                                {"error": str(e), "code": e.code, "detail": e.detail},
                                ensure_ascii=False
                            ),
                            tool_call_id=tool_call["id"]
                        )
                    )
                except Exception as e:
                    step_log.error = str(e)
                    step_log.error_code = "TOOL_ERROR"
                    step_log.error_detail = {"exception": type(e).__name__}
                    log.error(f"工具执行失败: {tool_name} - {e}")

                    messages.append(
                        ToolMessage(
                            content=json.dumps(
                                {"error": str(e), "code": "TOOL_ERROR"},
                                ensure_ascii=False
                            ),
                            tool_call_id=tool_call["id"]
                        )
                    )

                trace.add_step(step_log)

        log.warning(f"达到最大步数限制: {self.max_steps}")
        return {
            "answer": "抱歉，分析步骤超过限制，请简化问题或联系管理员。",
            "trace": trace.to_dict(),
            "steps": self.max_steps,
            "error": "达到最大步数限制",
            "error_code": "MAX_STEPS_EXCEEDED",
            "error_detail": {"max_steps": self.max_steps}
        }


class StreamingLLMAgent(LLMAgent):
    """支持流式输出的 LLM Agent"""

    async def run_stream(self, user_query: str, dataset_id: Optional[str] = None):
        """
        运行流式 Tool Calling 循环

        Yields:
            事件字典，包含 type 和相关数据
        """
        import time
        import asyncio

        trace = TraceContext()
        log.info(f"开始流式分析: trace_id={trace.trace_id}")

        # 发送开始事件
        yield {"type": "start", "trace_id": trace.trace_id}

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"数据集ID: {dataset_id}\n\n用户问题: {user_query}" if dataset_id else user_query)
        ]

        charts = []
        tables = []
        table_index = 0

        for step in range(self.max_steps):
            log.info(f"执行步骤 {step + 1}/{self.max_steps}")

            # 发送步骤开始事件
            yield {"type": "step_start", "step": step + 1, "max_steps": self.max_steps}

            try:
                response = await asyncio.to_thread(self.llm_with_tools.invoke, messages)
            except (OpenAIBadRequestError, OpenAIAPIError) as e:
                error_msg = self._parse_api_error(e, "OpenAI")
                error_code = "LLM_BAD_REQUEST" if isinstance(e, OpenAIBadRequestError) else "LLM_API_ERROR"
                log.error(f"OpenAI API 错误: {error_msg}")
                yield {
                    "type": "error",
                    "message": error_msg,
                    "trace": trace.to_dict(),
                    "error_code": error_code,
                    "error_detail": {"provider": "OpenAI", "exception": type(e).__name__}
                }
                return
            except (AnthropicBadRequestError, AnthropicAPIError) as e:
                error_msg = self._parse_api_error(e, "Anthropic")
                error_code = "LLM_BAD_REQUEST" if isinstance(e, AnthropicBadRequestError) else "LLM_API_ERROR"
                log.error(f"Anthropic API 错误: {error_msg}")
                yield {
                    "type": "error",
                    "message": error_msg,
                    "trace": trace.to_dict(),
                    "error_code": error_code,
                    "error_detail": {"provider": "Anthropic", "exception": type(e).__name__}
                }
                return
            except Exception as e:
                error_msg = f"LLM 调用失败: {str(e)}"
                log.error(error_msg)
                yield {
                    "type": "error",
                    "message": error_msg,
                    "trace": trace.to_dict(),
                    "error_code": "LLM_CALL_FAILED",
                    "error_detail": {"exception": type(e).__name__}
                }
                return

            # 提取 token 使用量
            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                if 'token_usage' in metadata:
                    usage = metadata['token_usage']
                    trace.llm_tokens += usage.get('total_tokens', 0)
                    input_cost = usage.get('prompt_tokens', 0) * 0.00001
                    output_cost = usage.get('completion_tokens', 0) * 0.00003
                    trace.llm_cost_usd += input_cost + output_cost
                elif 'usage' in metadata:
                    usage = metadata['usage']
                    trace.llm_tokens += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                    input_cost = usage.get('input_tokens', 0) * 0.000003
                    output_cost = usage.get('output_tokens', 0) * 0.000015
                    trace.llm_cost_usd += input_cost + output_cost

            if not response.tool_calls:
                # 最终答案
                final_answer = response.content

                # 发送答案事件（分块发送以模拟流式效果）
                chunk_size = 50
                for i in range(0, len(final_answer), chunk_size):
                    chunk = final_answer[i:i + chunk_size]
                    yield {"type": "answer_chunk", "content": chunk}

                # 发送完成事件
                yield {
                    "type": "complete",
                    "answer": final_answer,
                    "charts": charts,
                    "tables": tables,
                    "trace": trace.to_dict(),
                    "steps": step + 1
                }
                return

            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # 发送工具调用事件
                yield {"type": "tool_call", "tool": tool_name, "args": tool_args}

                step_log = StepLog(
                    tool=tool_name,
                    args=tool_args,
                    timestamp=datetime.now()
                )

                try:
                    start = time.time()
                    result = await asyncio.to_thread(self.tool_executor.execute, tool_name, tool_args)
                    step_log.latency_ms = (time.time() - start) * 1000
                    step_log.result = result

                    # 收集图表和表格
                    if tool_name == "plot" and result:
                        charts.append(result)
                    elif tool_name == "run_query" and result:
                        table_index += 1
                        tables.append({
                            "name": f"查询结果_{table_index}",
                            "columns": result.get("columns", []),
                            "rows": result.get("rows", [])
                        })

                    messages.append(
                        ToolMessage(
                            content=json.dumps(result, ensure_ascii=False),
                            tool_call_id=tool_call["id"]
                        )
                    )

                    # 发送工具结果事件
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "success": True,
                        "latency_ms": step_log.latency_ms
                    }

                except ToolExecutionError as e:
                    step_log.error = str(e)
                    step_log.error_code = e.code
                    step_log.error_detail = e.detail
                    log.error(f"工具执行失败: {tool_name} - {e}")

                    messages.append(
                        ToolMessage(
                            content=json.dumps(
                                {"error": str(e), "code": e.code, "detail": e.detail},
                                ensure_ascii=False
                            ),
                            tool_call_id=tool_call["id"]
                        )
                    )

                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "success": False,
                        "error": str(e),
                        "error_code": e.code,
                        "error_detail": e.detail
                    }
                except Exception as e:
                    step_log.error = str(e)
                    step_log.error_code = "TOOL_ERROR"
                    step_log.error_detail = {"exception": type(e).__name__}
                    log.error(f"工具执行失败: {tool_name} - {e}")

                    messages.append(
                        ToolMessage(
                            content=json.dumps(
                                {"error": str(e), "code": "TOOL_ERROR"},
                                ensure_ascii=False
                            ),
                            tool_call_id=tool_call["id"]
                        )
                    )

                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "success": False,
                        "error": str(e),
                        "error_code": "TOOL_ERROR",
                        "error_detail": {"exception": type(e).__name__}
                    }

                trace.add_step(step_log)

        # 达到最大步数
        yield {
            "type": "complete",
            "answer": "抱歉，分析步骤超过限制，请简化问题或联系管理员。",
            "charts": charts,
            "tables": tables,
            "trace": trace.to_dict(),
            "steps": self.max_steps,
            "error": "达到最大步数限制",
            "error_code": "MAX_STEPS_EXCEEDED",
            "error_detail": {"max_steps": self.max_steps}
        }


def get_llm_agent(llm_config: Optional[Dict[str, Any]] = None) -> LLMAgent:
    """获取 LLMAgent 实例"""
    return LLMAgent(llm_config)


def get_streaming_llm_agent(llm_config: Optional[Dict[str, Any]] = None) -> StreamingLLMAgent:
    """获取流式 LLMAgent 实例"""
    return StreamingLLMAgent(llm_config)

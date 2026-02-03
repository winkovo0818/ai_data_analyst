 通用结构化数据分析与可视化系统（LLM Tool Calling 架构）

## 1. 项目背景与目标
在企业数据分析场景中，用户希望通过自然语言完成以下任务：

+ 上传 Excel / CSV 等结构化数据
+ 使用自然语言提问（如趋势、对比、占比、异常）
+ 系统自动完成：
    - 数据理解
    - 安全计算
    - 结果可视化
    - 结论总结

本项目目标是构建一个**通用、可扩展、可上线的 AI 数据分析后端系统**，而不是一个“让模型写代码跑”的 Demo。

### 设计原则
+ ❌ 不允许 LLM 执行任意代码
+ ❌ 不允许 LLM 直接写 SQL / Python
+ ✅ LLM 只能调用**受限工具（Tools）**
+ ✅ 所有计算由后端确定性执行
+ ✅ 全流程可审计、可限流、可计费

## 2.总体架构
```python
User
 │
 │  自然语言问题
 ▼
API Server (FastAPI)
 │
 │  tool calling loop
 ▼
LLM (Planner / Narrator)
 │
 │  JSON tool calls
 ▼
Tool Executor (Backend)
 │
 ├── Dataset Manager (Excel / CSV / DuckDB)
 ├── Query Engine (QuerySpec → SQL)
 ├── Plot Engine (PlotSpec → ECharts / PNG)
 └── Audit / Logging / Cost

```

##  3.核心抽象模型
### 3.1 Dataset（数据集）
任何数据文件在系统中都会被抽象为 Dataset：  

Dataset 是 **LLM 不可修改、只可读取的对象**

```json
{
  "dataset_id": "ds_abc123",
  "source_type": "excel",
  "schema": [
    {"name": "账号", "type": "string"},
    {"name": "月份", "type": "string"},
    {"name": "退货数量", "type": "int"},
    {"name": "产品质量", "type": "int"}
  ],
  "row_count": 12034
}

```

### 3.2 Tool（工具）  
LLM 只能调用系统预定义的 Tool，每个 Tool 都有严格的 JSON Schema。 

| 类别 | 作用 |
| --- | --- |
| 数据探索 | 理解数据结构 |
| 数据查询 | 安全执行聚合/过滤 |
| 可视化 | 生成图表 |
| 辅助解析 | 字段语义映射 |


##  4.Tool 设计
### 4.1 create_dataset
将上传文件注册为 Dataset。  

```json
{
  "file_id": "file_xxx",
  "sheet": "Sheet1",
  "header_row": 1
}

```

返回：

```json
{
  "dataset_id": "ds_abc123"
}
```

### 4.2  get_schema
获取字段结构与统计信息

```json
{
  "dataset_id": "ds_abc123"
}
```

返回：

```json
{
  "columns": [
    {
      "name": "退货数量",
      "type": "int",
      "null_ratio": 0.0,
      "example_values": [12, 35, 8]
    }
  ]
}

```

### 4.3 sample_rows
```json
{
  "dataset_id": "ds_abc123",
  "n": 5,
  "columns": ["账号","月份","退货数量"]
}

```

### 4.4  run_query
LLM **只能生成 QuerySpec JSON，不允许 SQL / Python**

**QuerySpec 定义**

```json
{
  "filters": [
    {"col": "年份", "op": "=", "value": 2025}
  ],
  "group_by": ["账号","月份"],
  "aggregations": [
    {"as": "return_qty", "agg": "sum", "col": "退货数量"},
    {"as": "quality_cnt", "agg": "sum", "col": "产品质量"}
  ],
  "derived": [
    {
      "as": "quality_rate",
      "expr": "quality_cnt / nullif(return_qty, 0)"
    }
  ],
  "sort": [{"col": "月份", "dir": "asc"}],
  "limit": 5000
}

```

支持的操作白名单：

+ `op`：`= != > >= < <= in between contains is_null`
+ `agg`：`sum avg min max count nunique`
+ `expr`：`+ - * / nullif coalesce round abs`
+ 最大行数：10,000

### 4.5   plot
```json
{
  "chart_type": "line",
  "title": "2025 各账号产品质量占比趋势",
  "x": "月份",
  "y": "quality_rate",
  "series": "账号",
  "y_format": "percent"
}

```

返回：

+ ECharts option JSON  
**或 **PNG/base64 图片

### 4.6   resolve_fields
 用于语义字段映射

```json
{
  "dataset_id": "ds_abc123",
  "terms": ["退货原因","质量问题"]
}
```

返回：

```json
{
  "mapped_columns": ["产品质量","物流异常","购买风险"]
}
```

##  5. Tool Calling 执行循环
 后端核心逻辑（简化）：  

```python
for step in range(MAX_STEPS):
    resp = llm(messages, tools)

    if resp.is_tool_call:
        validate_schema(resp.args)
        result = execute_tool(resp)
        messages.append(tool_result)
    else:
        return final_answer

```

### 强约束
+ 最大 6～8 步
+ 每步必须产生新数据
+ tool 参数必须校验
+ 超限 / 失败 → 中止并返回原因

##  6. Prompt 设计（System Prompt） 
```python
你是一个数据分析规划助手。
你不能直接计算、不能编造数据。
你必须：
1. 先理解 schema
2. 再调用 run_query 进行计算
3. 所有结论必须基于 tool 返回结果
4. 若字段不存在，必须先调用 resolve_fields
5. 不确定时，不要猜测，必须请求更多信息
```

##  7. 返回结果结构（统一）
```json
{
  "answer": "2025 年 Amazon_XX_XX 账号中，产品质量类退货在 1-3 月呈上升趋势...",
  "tables": [
    {
      "name": "aggregated_data",
      "rows": [...]
    }
  ],
  "charts": [
    {
      "type": "line",
      "option": {...}
    }
  ],
  "audit": {
    "steps": [
      {"tool": "get_schema", "latency_ms": 30},
      {"tool": "run_query", "rows": 120}
    ],
    "trace_id": "xxx",
    "llm_cost_usd": 0.012
  }
}
```

##   8.  安全与稳定性设计
### 安全
+ 不执行任意代码
+ 不暴露原始文件给 LLM
+ Tool 参数双重校验（schema + 语义）
+ Prompt 注入防护（忽略数据内指令）

### 稳定性
+ 行数 / 字段数 / step 数限制
+ Query 复杂度限制
+ Tool 超时保护
+ 缓存（schema / embedding / query result）

##   9. 技术选型建议
+ API：FastAPI
+ 执行引擎：DuckDB（Excel/CSV → SQL）
+ 校验：Pydantic v2
+ 日志：JSON + trace_id
+ 图表：ECharts / matplotlib
+ **LangChain**：工具（Tools）、模型封装、输出解析、回调体系  

##  10. MVP 验收标准
+ 能分析任意 Excel 的：
+ 聚合
+ 趋势
+ 占比
+ LLM 不产生任何“凭空数字”
+ 任意 tool 调用可回放
+ 可在 10 万行内稳定运行
+ 成本、耗时可观测



设计并实现通用型 AI 数据分析后端系统，通过 Tool Calling 与受限 Query DSL，将自然语言问题安全映射为结构化查询与可视化结果，避免 LLM 幻觉并支持审计与扩展。  


# 系统架构文档

## 整体架构

```
┌─────────────┐
│   用户请求   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   FastAPI Server    │
│  (API Gateway)      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│    LLM Agent        │
│  (Tool Calling)     │
└──────┬──────────────┘
       │
       ├─────────────┬──────────────┬──────────────┐
       ▼             ▼              ▼              ▼
┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐
│ Dataset  │  │  Query    │  │   Plot   │  │  Tool    │
│ Manager  │  │  Engine   │  │  Engine  │  │ Executor │
└────┬─────┘  └─────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                    │
                    ▼
            ┌───────────────┐
            │    DuckDB     │
            │  (Data Store) │
            └───────────────┘
```

## 核心模块

### 1. API Layer (src/api)

**职责**: 接收 HTTP 请求，路由到相应处理器

**关键文件**:
- `main.py`: FastAPI 应用入口
  - `/upload`: 文件上传接口
  - `/dataset/create`: 创建数据集
  - `/analyze`: 数据分析接口

**技术栈**: FastAPI, Pydantic, Uvicorn

### 2. LLM Agent (src/engines/llm_agent.py)

**职责**: Tool Calling 循环控制

**工作流程**:
1. 接收用户问题
2. 调用 LLM（带工具定义）
3. 解析工具调用请求
4. 执行工具（通过 Tool Executor）
5. 收集结果，继续下一轮
6. 返回最终答案

**关键特性**:
- 最大步数限制（防止死循环）
- 完整的 trace 记录
- 成本计算
- 错误处理

### 3. Tool Executor (src/engines/tool_executor.py)

**职责**: 执行具体的工具调用

**支持的工具**:
- `create_dataset`: 注册数据集
- `get_schema`: 获取字段结构
- `sample_rows`: 获取样本数据
- `run_query`: 执行查询
- `plot`: 生成图表
- `resolve_fields`: 字段语义映射

**安全机制**:
- 参数 Schema 校验
- 白名单操作符
- 超时保护
- 异常捕获

### 4. Dataset Manager (src/engines/dataset_manager.py)

**职责**: 数据集生命周期管理

**功能**:
- Excel/CSV 文件解析
- Schema 自动提取
- 数据存储到 DuckDB
- 样本数据获取
- 元数据管理

**数据流**:
```
上传文件 → Pandas 读取 → Schema 提取 → DuckDB 存储 → 元数据缓存
```

### 5. Query Engine (src/engines/query_engine.py)

**职责**: QuerySpec DSL → SQL 转换

**QuerySpec 结构**:
```json
{
  "dataset_id": "ds_xxx",
  "filters": [{"col": "年份", "op": "=", "value": 2025}],
  "group_by": ["账号", "月份"],
  "aggregations": [{"as": "total", "agg": "sum", "col": "退货数量"}],
  "derived": [{"as": "rate", "expr": "quality / total"}],
  "sort": [{"col": "月份", "dir": "asc"}],
  "limit": 1000
}
```

**安全约束**:
- 操作符白名单
- 聚合函数白名单
- 表达式白名单
- 行数限制

**SQL 生成流程**:
```
QuerySpec → 校验 → 构建 SELECT → 构建 WHERE → 构建 GROUP BY → 执行
```

### 6. Plot Engine (src/engines/plot_engine.py)

**职责**: 数据可视化

**支持的图表**:
- Line Chart (折线图)
- Bar Chart (柱状图)
- Pie Chart (饼图)
- Scatter Chart (散点图)
- Area Chart (面积图)

**输出格式**:
- ECharts option JSON
- PNG base64 (可选)

## 数据模型

### 核心模型 (src/models)

```
dataset.py
├── ColumnSchema        # 列 Schema
├── DatasetMetadata     # 数据集元数据
└── DatasetSample       # 样本数据

query.py
├── FilterCondition     # 过滤条件
├── Aggregation         # 聚合定义
├── DerivedField        # 衍生字段
├── SortSpec            # 排序规则
├── QuerySpec           # 查询规范
└── QueryResult         # 查询结果

plot.py
├── PlotSpec            # 图表规范
└── ChartOutput         # 图表输出

response.py
├── AnalysisResponse    # 分析响应
└── UploadResponse      # 上传响应
```

## 安全设计

### 1. 代码执行隔离

- ❌ LLM 不能执行任意代码
- ❌ LLM 不能直接写 SQL
- ✅ LLM 只能调用预定义工具
- ✅ 工具参数严格校验

### 2. SQL 注入防护

- 操作符白名单
- 列名校验
- 值参数化
- 表达式白名单

### 3. Prompt 注入防护

- 数据与指令分离
- 关键词检测
- 内容过滤

### 4. 资源限制

- 查询行数限制 (10,000)
- 工具步数限制 (8)
- 文件大小限制 (50 MB)
- 查询超时 (30s)

## 可观测性

### 1. 日志系统 (Loguru)

```python
log.info("执行查询")      # 信息日志
log.warning("速率限制")   # 警告日志
log.error("查询失败")     # 错误日志
```

### 2. Trace 系统

每次请求生成唯一 `trace_id`，记录：
- 每步工具调用
- 参数和结果
- 执行耗时
- 错误信息

### 3. 成本计算

- LLM Token 消耗
- API 调用成本
- 总耗时

## 扩展性设计

### 1. 添加新工具

```python
# 1. 定义 Tool Schema (src/tools/new_tool.py)
class NewToolInput(BaseModel):
    param: str

# 2. 注册到 TOOL_REGISTRY (src/tools/__init__.py)
TOOL_REGISTRY["new_tool"] = {...}

# 3. 实现执行逻辑 (src/engines/tool_executor.py)
def _execute_new_tool(self, args):
    return result
```

### 2. 支持新数据源

```python
# 扩展 Dataset Manager
def create_dataset_from_postgres(self, connection_string):
    df = pd.read_sql(query, connection_string)
    return self._create_from_dataframe(df)
```

### 3. 支持新图表类型

```python
# 扩展 Plot Engine
def _generate_heatmap(self, spec: PlotSpec):
    return echarts_option
```

## 部署架构

### 单机部署

```
┌─────────────────────┐
│   Nginx (可选)      │
│   ↓                 │
│   FastAPI (Uvicorn) │
│   ↓                 │
│   DuckDB (本地文件) │
└─────────────────────┘
```

### 分布式部署（未来）

```
┌──────────┐     ┌──────────┐
│ API Node │ ... │ API Node │
└────┬─────┘     └────┬─────┘
     │                │
     └────────┬───────┘
              ▼
      ┌──────────────┐
      │ PostgreSQL   │
      │ (替代DuckDB) │
      └──────────────┘
              ▼
      ┌──────────────┐
      │  Redis Cache │
      └──────────────┘
```

## 性能优化

### 1. 缓存策略

- Schema 缓存（避免重复读取）
- Query 结果缓存
- LLM 响应缓存（相同问题）

### 2. 数据库优化

- DuckDB 列式存储
- 自动索引
- 查询计划优化

### 3. 并发控制

- 异步 IO (FastAPI)
- 连接池
- 速率限制

## 监控指标

### 关键指标

- QPS (每秒请求数)
- 平均响应时间
- P95/P99 延迟
- 错误率
- LLM Token 消耗
- 数据集数量
- 存储使用量

### 告警规则

- 错误率 > 5%
- P95 延迟 > 10s
- 磁盘使用 > 80%
- 内存使用 > 90%

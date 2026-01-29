# AI Data Analyst - 通用结构化数据分析与可视化系统

基于Langchain架构的企业级AI数据分析系统。

## 核心特性

- 通过自然语言分析 Excel/CSV 数据
- LLM 只调用受限工具，不执行任意代码
- 安全的 QuerySpec DSL，避免 SQL 注入
- 自动生成可视化图表（ECharts/PNG）
- 全流程可审计、可限流、可计费
- 支持 10 万行级别数据稳定运行
- 支持流式响应（SSE），实时查看分析进度

## 架构设计

```
User → FastAPI → LLM (Tool Calling) → Tool Executor
                                        ├── Dataset Manager (DuckDB)
                                        ├── Query Engine (QuerySpec → SQL)
                                        ├── Plot Engine (ECharts/PNG)
                                        └── Audit & Logging
```

## 快速开始

### 1. 后端安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 LLM API Key
```

### 2. 前端安装

```bash
cd frontend
npm install
```

### 3. 启动服务

**后端服务**（终端1）：
```bash
python run.py
```

**前端服务**（终端2）：
```bash
cd frontend
npm run dev
```

访问：
- 前端界面: http://localhost:3000
- 后端 API: http://localhost:8000/docs

## API 端点

### 基础端点
| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 系统信息 |
| `/health` | GET | 健康检查 |

### 文件管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/upload` | POST | 上传数据文件（Excel/CSV） |

### 数据集管理
| 端点 | 方法 | 说明 |
|------|------|------|
| `/dataset/create` | POST | 创建数据集 |
| `/dataset/{id}/schema` | GET | 获取数据集结构 |

### 数据分析
| 端点 | 方法 | 说明 |
|------|------|------|
| `/analyze` | POST | 同步分析请求 |
| `/analyze/stream` | POST | 流式分析请求（SSE） |

## 核心工具 (Tools)

系统提供 6 个受限工具供 LLM 调用：

| 工具 | 功能 | 说明 |
|------|------|------|
| `create_dataset` | 注册数据集 | 将上传文件注册为可查询的数据集 |
| `get_schema` | 获取字段结构 | 返回列名、类型、统计信息 |
| `sample_rows` | 获取样本数据 | 返回前N行数据供LLM理解 |
| `run_query` | 执行安全查询 | 基于 QuerySpec DSL 执行查询 |
| `plot` | 生成图表 | 支持折线图/柱状图/饼图（ECharts/PNG） |
| `resolve_fields` | 语义字段映射 | 将用户自然语言映射到实际字段名 |

## 核心引擎

| 引擎 | 功能 |
|------|------|
| `dataset_manager` | 数据集管理，基于 DuckDB |
| `query_engine` | 查询引擎，QuerySpec → SQL 转换 |
| `plot_engine` | 图表生成，支持 ECharts 和 PNG |
| `tool_executor` | 工具执行器，管理工具调用 |
| `llm_agent` | LLM 代理，处理 Tool Calling 逻辑 |

## 项目结构

```
ai_data_analyst/
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API 服务层
│   │   └── utils/          # 工具函数
│   └── package.json
├── src/
│   ├── core/               # 核心配置与常量
│   │   ├── config.py       # 系统配置
│   │   └── constants.py    # 常量定义
│   ├── models/             # Pydantic 数据模型
│   │   ├── query.py        # 查询请求模型
│   │   ├── plot.py         # 图表配置模型
│   │   ├── response.py     # API 响应模型
│   │   └── dataset.py      # 数据集元数据模型
│   ├── tools/              # Tool 定义与实现
│   ├── engines/            # 核心引擎
│   ├── api/                # FastAPI 路由
│   └── utils/              # 工具函数
│       ├── logger.py       # 日志管理
│       ├── trace.py        # 调用链追踪
│       ├── security.py     # 安全防护
│       └── rate_limiter.py # 速率限制
├── data/
│   ├── uploads/            # 上传文件存储
│   └── duckdb/             # DuckDB 数据库文件
├── logs/                   # 日志文件
└── tests/                  # 测试用例
```

## 配置说明

### LLM 配置
- 支持 OpenAI 和 Anthropic 双提供商
- 可配置默认模型（如 gpt-4-turbo-preview）
- 支持自定义 API Key

### 安全限制
| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `max_tool_steps` | 8 | 最大工具调用步数 |
| `max_query_rows` | 10000 | 单次查询最大行数 |
| `max_upload_size_mb` | 50 | 文件上传大小限制 |
| `query_timeout_seconds` | 30 | 查询超时时间 |

## 安全设计

- LLM 不能执行任意代码
- LLM 不能直接写 SQL/Python
- 所有操作通过白名单工具
- QuerySpec 参数严格校验（Pydantic v2）
- 行数/步数/复杂度限制
- Prompt 注入防护
- 请求速率限制（基于 IP）

## 可观测性

- 全流程审计日志
- Tool 调用链可回放
- 成本和耗时监控
- 详细的 Trace 信息

## 技术栈

### 后端
- **Web**: FastAPI + Uvicorn
- **数据**: DuckDB + Pandas
- **校验**: Pydantic v2
- **LLM**: LangChain
- **日志**: Loguru

### 前端
- **框架**: React 18 + Vite 5
- **UI**: Ant Design 5
- **图表**: ECharts 5
- **HTTP**: Axios

## 功能亮点

- **安全可控**: LLM 只能调用预定义的白名单工具
- **高性能**: 基于 DuckDB 列式存储，支持 10 万行数据
- **实时响应**: 流式 SSE 推送分析进度
- **多格式支持**: Excel（多 Sheet）、CSV
- **灵活配置**: 支持自定义 LLM 提供商和模型
- **全链路追踪**: 所有操作可审计、可回放

## 开发计划

详见 [AI Data Analyst.md](./AI%20Data%20Analyst.md)

## License

MIT

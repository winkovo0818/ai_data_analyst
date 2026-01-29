# 使用指南

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置文件
cp .env .env

# 编辑 .env，填入你的 API Key
# OPENAI_API_KEY=sk-xxx
# 或
# ANTHROPIC_API_KEY=sk-ant-xxx
```

### 3. 启动服务

```bash
python run.py
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

## API 使用示例

### 1. 上传文件

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@data.xlsx"
```

响应：
```json
{
  "file_id": "data.xlsx",
  "filename": "data.xlsx",
  "size_bytes": 12345,
  "sheets": ["Sheet1", "Sheet2"]
}
```

### 2. 创建数据集

```bash
curl -X POST "http://localhost:8000/dataset/create" \
  -F "file_id=data.xlsx" \
  -F "sheet=Sheet1" \
  -F "header_row=1"
```

响应：
```json
{
  "dataset_id": "ds_abc123",
  "row_count": 1000,
  "column_count": 10,
  "schema": [...]
}
```

### 3. 分析数据

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "2025年各账号的退货数量趋势是什么？",
    "dataset_id": "ds_abc123"
  }'
```

响应：
```json
{
  "answer": "2025年各账号退货数量呈现以下趋势...",
  "tables": [...],
  "charts": [...],
  "audit": {
    "trace_id": "xxx",
    "steps": [...],
    "llm_cost_usd": 0.012
  }
}
```

## Python 示例

```python
import requests

# 1. 上传文件
with open("data.xlsx", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": f}
    )
    file_info = response.json()
    print(f"文件ID: {file_info['file_id']}")

# 2. 创建数据集
response = requests.post(
    "http://localhost:8000/dataset/create",
    data={
        "file_id": file_info["file_id"],
        "sheet": "Sheet1",
        "header_row": 1
    }
)
dataset = response.json()
dataset_id = dataset["dataset_id"]
print(f"数据集ID: {dataset_id}")

# 3. 分析数据
response = requests.post(
    "http://localhost:8000/analyze",
    json={
        "question": "各月份的平均退货数量是多少？",
        "dataset_id": dataset_id
    }
)
result = response.json()
print(f"答案: {result['answer']}")
print(f"步数: {result['audit']['total_steps']}")
print(f"成本: ${result['audit']['llm_cost_usd']}")
```

## 支持的查询类型

### 1. 聚合分析

问题示例：
- "各账号的总退货数量是多少？"
- "每月的平均产品质量分数是多少？"
- "最大和最小的退货数量分别是多少？"

### 2. 趋势分析

问题示例：
- "2025年各月的退货数量趋势"
- "产品质量随时间的变化"
- "各账号的月度退货趋势对比"

### 3. 占比分析

问题示例：
- "各账号的退货占比"
- "不同退货原因的分布"
- "各产品类别的销售占比"

### 4. 过滤分析

问题示例：
- "2025年1月的退货数据"
- "退货数量大于100的记录"
- "Amazon账号的所有数据"

## 注意事项

1. **数据安全**
   - 所有数据仅在本地处理
   - LLM 不能执行任意代码
   - 只能调用预定义的安全工具

2. **性能限制**
   - 单次查询最多返回 10,000 行
   - 工具调用最多 8 步
   - 文件大小限制 50 MB

3. **成本控制**
   - 每次分析会产生 LLM API 费用
   - 建议使用 GPT-4 Turbo 或 Claude 3.5 Sonnet
   - 可通过 audit 信息查看成本

4. **最佳实践**
   - 问题描述清晰具体
   - 大数据集建议先采样分析
   - 复杂分析可拆分为多个问题

# AI Data Analyst - 完整部署指南

## 本地开发环境

### 1. 后端部署

```bash
# 克隆项目
git clone <repository>
cd ai_data_analyst

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp .env .env
# 编辑 .env，填入以下内容：
# OPENAI_API_KEY=sk-xxx  # 或使用 ANTHROPIC_API_KEY

# 启动后端
python run.py
```

后端服务运行在 http://localhost:8000

### 2. 前端部署

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务运行在 http://localhost:3000

## 生产环境部署

### 方案一：单服务器部署（推荐）

使用 Nginx 反向代理，同时服务前后端。

#### 1. 构建前端

```bash
cd frontend
npm run build
# 构建产物在 frontend/dist/
```

#### 2. 配置 Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/ai_data_analyst/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 文件上传限制
    client_max_body_size 50M;
}
```

#### 3. 启动后端（使用 Supervisor）

创建 `/etc/supervisor/conf.d/ai_data_analyst.conf`:

```ini
[program:ai_data_analyst]
command=/path/to/venv/bin/python run.py
directory=/path/to/ai_data_analyst
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ai_data_analyst.log
```

启动服务：
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ai_data_analyst
```

### 方案二：Docker 部署

#### 1. 创建 Dockerfile（后端）

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

#### 2. 创建 Dockerfile（前端）

```dockerfile
FROM node:18-alpine as build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

#### 3. docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEFAULT_LLM_PROVIDER=openai
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
```

启动：
```bash
docker-compose up -d
```

### 方案三：云平台部署

#### Vercel（前端）+ Railway（后端）

**前端（Vercel）**:
1. 连接 GitHub 仓库
2. 设置构建目录: `frontend`
3. 构建命令: `npm run build`
4. 输出目录: `dist`
5. 环境变量: `VITE_API_URL=https://your-backend.railway.app`

**后端（Railway）**:
1. 连接 GitHub 仓库
2. 选择 Python 环境
3. 添加环境变量: `OPENAI_API_KEY`
4. 部署命令: `python run.py`

## 环境变量配置

### 后端 (.env)

```bash
# LLM API Keys
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# LLM 配置
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4-turbo-preview

# 系统限制
MAX_TOOL_STEPS=8
MAX_QUERY_ROWS=10000
MAX_UPLOAD_SIZE_MB=50
QUERY_TIMEOUT_SECONDS=30

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# 存储路径
UPLOAD_DIR=./data/uploads
DUCKDB_DIR=./data/duckdb

# 日志
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

### 前端（生产环境）

修改 `frontend/src/services/api.js`:

```javascript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 60000,
});
```

## 性能优化

### 1. 后端优化

```python
# 使用 Gunicorn 替代 Uvicorn
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 2. 前端优化

```bash
# 启用 gzip 压缩
# 在 Nginx 配置中：
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# 设置缓存
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 3. 数据库优化

```python
# 使用连接池
# 定期清理过期数据集
# 添加索引
```

## 监控与日志

### 1. 后端日志

日志存储在 `logs/app.log`，使用 Loguru 格式化。

### 2. 前端错误追踪

可集成 Sentry:

```bash
npm install @sentry/react
```

### 3. 系统监控

推荐工具：
- Prometheus + Grafana（指标监控）
- ELK Stack（日志聚合）
- Uptime Kuma（可用性监控）

## 备份策略

### 1. 数据备份

```bash
# 定时备份 DuckDB 数据库和上传文件
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```

### 2. 配置备份

```bash
# 备份环境变量和配置
cp .env .env.backup
```

## 安全建议

1. **API Key 安全**
   - 使用环境变量，不要硬编码
   - 定期轮换 API Key
   - 使用 secrets 管理工具

2. **文件上传安全**
   - 限制文件类型和大小
   - 扫描上传文件
   - 隔离存储

3. **访问控制**
   - 添加用户认证（JWT）
   - 实施速率限制
   - HTTPS 加密传输

4. **CORS 配置**
   - 生产环境限制允许的域名
   - 不要使用 `allow_origins=["*"]`

## 故障排查

### 常见问题

1. **后端启动失败**
   - 检查端口占用: `netstat -ano | findstr 8000`
   - 检查环境变量配置
   - 查看日志: `tail -f logs/app.log`

2. **前端无法连接后端**
   - 检查代理配置
   - 确认后端服务运行
   - 检查 CORS 设置

3. **文件上传失败**
   - 检查文件大小限制
   - 确认存储目录权限
   - 查看 Nginx 限制

4. **LLM 调用失败**
   - 验证 API Key 有效性
   - 检查网络连接
   - 查看 API 配额

## 成本优化

1. **LLM 成本**
   - 使用 GPT-3.5 Turbo 替代 GPT-4（成本降低 90%）
   - 实现结果缓存
   - 优化 Prompt 长度

2. **服务器成本**
   - 使用 CDN 缓存静态资源
   - 数据库定期清理
   - 按需扩容

## 更新维护

### 依赖更新

```bash
# 后端
pip list --outdated
pip install -U package_name

# 前端
npm outdated
npm update
```

### 数据库迁移

```bash
# 备份现有数据
# 执行迁移脚本
# 验证数据完整性
```

---

部署完成后，建议进行完整的端到端测试，确保所有功能正常运行。

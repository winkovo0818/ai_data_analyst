# AI Data Analyst - Frontend

基于 React + Vite + Ant Design + ECharts 的现代化前端界面。

## 功能特性

- 📁 **文件上传**: 支持拖拽上传 Excel/CSV 文件
- 📊 **数据集管理**: 创建和查看数据集信息
- 💬 **智能对话**: 自然语言数据分析
- 📈 **可视化**: ECharts 图表自动生成
- 📋 **表格展示**: Ant Design 表格组件
- 🎯 **审计追踪**: 查看执行步骤和成本

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
```

## 技术栈

- **框架**: React 18
- **构建工具**: Vite 5
- **UI 组件**: Ant Design 5
- **图表库**: ECharts 5 + echarts-for-react
- **HTTP 客户端**: Axios
- **图标**: Ant Design Icons

## 项目结构

```
frontend/
├── src/
│   ├── components/          # React 组件
│   │   ├── FileUpload.jsx   # 文件上传组件
│   │   ├── ChatInterface.jsx # 对话界面
│   │   ├── ChartDisplay.jsx  # 图表展示
│   │   └── TableDisplay.jsx  # 表格展示
│   ├── services/            # API 服务
│   │   └── api.js           # API 封装
│   ├── App.jsx              # 主应用组件
│   ├── main.jsx             # 应用入口
│   └── index.css            # 全局样式
├── index.html               # HTML 模板
├── vite.config.js           # Vite 配置
└── package.json             # 依赖配置
```

## 主要功能

### 1. 文件上传
- 支持拖拽和点击上传
- Excel 文件可选择 Sheet
- 自定义表头行号

### 2. 数据分析
- 自然语言提问
- 实时流式响应
- 支持多轮对话

### 3. 结果展示
- 自然语言答案
- 表格数据（分页、排序）
- ECharts 图表（折线图、柱状图、饼图等）
- 审计信息（步数、成本、耗时）

## 环境变量

Vite 自动配置代理，将 `/api` 请求转发到后端服务器 `http://localhost:8000`

## 开发说明

### API 代理配置

在 `vite.config.js` 中配置：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

### 新增组件

所有组件放在 `src/components/` 目录下，使用 JSX 格式。

### API 调用

使用 `src/services/api.js` 中封装的方法：

```javascript
import { dataService } from '../services/api';

// 上传文件
const result = await dataService.uploadFile(file);

// 分析数据
const analysis = await dataService.analyze(question, datasetId);
```

## 部署

### 开发环境

```bash
npm run dev
```

### 生产环境

```bash
# 构建
npm run build

# 预览构建结果
npm run preview
```

构建产物在 `dist/` 目录，可部署到任何静态服务器（Nginx、Vercel、Netlify 等）。

## 注意事项

1. 确保后端服务已启动（`python run.py`）
2. 前端默认代理到 `http://localhost:8000`
3. 生产环境需配置正确的 API 地址
4. 图表数据格式需符合 ECharts 规范

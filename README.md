# Live2D Desktop Pet

一个基于 Live2D 的桌面宠物应用，支持 AI 对话功能。

## 项目结构

- `frontend/` - 前端应用 (Vue + Tauri)
- `backend/` - 后端服务 (Python FastAPI)
- `mcpserve/` - MCP 工具服务

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### MCP 服务

```bash
cd mcpserve
pip install -r requirements.txt
python main.py
```

## 技术栈

- 前端: Vue 3 + Vite + Tauri
- 后端: Python + FastAPI
- Live2D: Cubism SDK

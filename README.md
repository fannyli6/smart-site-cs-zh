# 智慧工地 AI 客服系统

基于 RAG 的垂直领域智能客服（需求文档 v1.0）。前后端分离：

- **后端** `backend/`：FastAPI + Chroma 向量库 + 阿里云百炼 Qwen（OpenAI 兼容）
- **前端** `frontend/`：Vue 3 + Vite 单页应用（微信式聊天 UI，移动端适配）

## 功能（对齐需求文档 P0）

- ✅ AI 对话问答（SSE 流式输出）
- ✅ 4 大领域选择（设备故障 / 安装实施 / 数据异常 / 对接政府）+ 意图自动识别
- ✅ 引用来源展示（文档名 + 章节 + 相似度，可展开原文）
- ✅ 知识库文档上传（PDF/Word/Excel/Markdown/TXT 自动解析、切片、向量化）
- ✅ 向量检索 → LLM 生成，答不出时引导人工客服
- ✅ 开机自动灌入 4 大领域种子 FAQ，开箱即用

## 目录结构

```
.
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── main.py     # 接口与 SSE
│   │   ├── rag.py      # 检索 + 生成
│   │   ├── intent.py   # 领域意图识别
│   │   ├── embed.py    # Embedding 客户端
│   │   ├── llm.py      # LLM 客户端（DashScope）
│   │   ├── store.py    # Chroma 向量库封装
│   │   ├── ingest.py   # 文档解析 + 切片
│   │   ├── seed_data.py# 种子 FAQ 知识
│   │   └── config.py   # 环境变量配置
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/           # Vue 前端
│   ├── src/App.vue
│   ├── src/api.js
│   ├── Dockerfile
│   └── default.conf.template   # nginx 反代 /api
├── deploy/             # Sealos 部署配置与说明
│   ├── README.md
│   └── sealos-template.json
└── docker-compose.yml  # 本地一键启动
```

## 环境变量（后端）

| 变量 | 说明 | 默认 |
|------|------|------|
| `DASHSCOPE_API_KEY` | **必填** 阿里云百炼 Key | 空 |
| `CHAT_MODEL` | 对话模型 | qwen-plus |
| `EMBED_MODEL` | 嵌入模型 | text-embedding-v3 |
| `EMBED_DIM` | 向量维度 | 1024 |
| `CHROMA_PERSIST_DIR` | 向量库路径 | ./data/chroma |

## 本地运行

```bash
export DASHSCOPE_API_KEY=sk-xxxx
docker compose up --build
# 前端 http://localhost:8080
```

或不依赖 Docker：

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# 前端（另开终端）
cd frontend
npm install && npm run dev   # http://localhost:5173
```

部署详见 [deploy/README.md](deploy/README.md)。

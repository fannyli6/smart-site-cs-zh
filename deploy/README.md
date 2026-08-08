# 智慧工地 AI 客服 — Sealos 部署指南

前后端分离部署：后端（FastAPI + Chroma）和前端（Vue + Nginx）是两个独立应用。

## 一、准备镜像

方式 A：本地构建后推送到镜像仓库（Docker Hub / 阿里云 ACR 等）
```bash
# 后端
docker build -t <你的仓库>/smart-site-cs-backend:1.0 ./backend
docker push <你的仓库>/smart-site-cs-backend:1.0

# 前端
docker build -t <你的仓库>/smart-site-cs-frontend:1.0 ./frontend
docker push <你的仓库>/smart-site-cs-frontend:1.0
```

方式 B：直接把本仓库推到 GitHub/GitLab，在 Sealos「App Launchpad」选择「从代码构建」，
分别指定 `backend/Dockerfile` 和 `frontend/Dockerfile` 即可，无需本地构建。

## 二、在 Sealos 部署后端（App Launchpad）

1. 进入 Sealos 桌面 → **App Launchpad** → 新建应用。
2. 镜像填 `<你的仓库>/smart-site-cs-backend:1.0`。
3. 容器端口：`8000`，协议 `HTTP`。
4. 环境变量（必填/选填）：
   | 变量 | 说明 | 示例 |
   |------|------|------|
   | `DASHSCOPE_API_KEY` | **必填**，阿里云百炼 API Key | sk-xxxx |
   | `CHAT_MODEL` | 对话模型，默认 qwen-plus | qwen-plus / qwen-max / qwen2.5-7b-instruct |
   | `EMBED_MODEL` | 嵌入模型，默认 text-embedding-v3 | text-embedding-v3 |
   | `EMBED_DIM` | 向量维度，需与模型一致，默认 1024 | 1024 |
   | `CHROMA_PERSIST_DIR` | 向量库路径，保持 `/app/data/chroma` | /app/data/chroma |
5. **持久卷（重要）**：挂载一个 PV 到 `/app/data`，否则重启后知识库丢失。
6. 开启「外网访问」，记下后端分配到的域名（如 `ai-cs-backend.xxxx.sealosb.com`）。

> 应用启动后会自动灌入「设备故障 / 安装实施 / 数据异常 / 对接政府」种子 FAQ，
> 无需先上传文档即可问答。

## 三、在 Sealos 部署前端（App Launchpad）

1. 新建应用，镜像填 `<你的仓库>/smart-site-cs-frontend:1.0`。
2. 容器端口：`80`，协议 `HTTP`。
3. 环境变量：
   | 变量 | 说明 | 示例 |
   |------|------|------|
   | `BACKEND_URL` | 后端地址。**同账号内部访问填内部地址** `http://ai-cs-backend:8000`；跨网络填后端外网域名 `https://ai-cs-backend.xxxx.sealosb.com` | 见上文 |
4. 开启「外网访问」，得到前端域名，浏览器打开即可使用。

## 四、验证

- 打开前端域名，发一条：「温湿度传感器一直掉线怎么办？」
- 应看到带「设备故障」标签的回答、可展开的参考来源，以及流式输出。
- 访问 `<后端域名>/api/health` 应返回 `{"status":"ok",...}`。

## 五、一键模板（可选）

`sealos-template.json` 为 App Launchpad 导入模板（尽力对齐官方 schema，若 UI 字段有差异，
以第二步/第三步手动填写为准）。在 App Launchpad 选择「导入模板」并上传该 JSON 即可。

## 六、本地运行（不走 Sealos）

```bash
export DASHSCOPE_API_KEY=sk-xxxx
docker compose up --build
# 前端 http://localhost:8080   后端 http://localhost:8000
```

## 七、知识库维护

- 前端界面点「📥 上传知识」，选领域后上传 PDF/Word/Excel/Markdown/TXT，自动解析切片入库。
- 也可用接口：`curl -F file=@手册.pdf -F domain=device_fault <后端域名>/api/upload`
- 查看统计：`<后端域名>/api/stats`

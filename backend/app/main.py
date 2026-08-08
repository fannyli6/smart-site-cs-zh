"""FastAPI 主应用：AI 客服后端。

接口：
  GET  /api/health          健康检查
  GET  /api/domains         4 大领域
  GET  /api/stats           知识库统计
  POST /api/chat            SSE 流式问答
  POST /api/upload          文档上传 + 自动索引（管理员）
"""
import json
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import config
from .rag import answer_stream, build_sources, prepare
from .ingest import ingest_bytes
from .store import count
from .seed import ensure_seed
from .schemas import ChatRequest

app = FastAPI(title="智慧工地 AI 客服", version="1.0.0")

# 允许前端跨域（前后端分离部署时端口不同）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    ensure_seed()


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/")
def root():
    # 兼容云平台默认健康检查探针（通常访问 /）
    return {"status": "ok", "service": "smart-site-ai-cs"}


@app.get("/api/health")
def health():
    return {"status": "ok", "chunks": count(), "has_key": bool(config.DASHSCOPE_API_KEY)}


@app.get("/api/domains")
def domains():
    return {"domains": [{"key": k, "label": v} for k, v in config.DOMAINS.items()]}


@app.get("/api/stats")
def stats():
    # 简单统计：总切片 + 按领域聚合（轻量实现）
    by_domain = {k: 0 for k in config.VALID_DOMAINS}
    try:
        from .store import get_metadatas
        for m in get_metadatas():
            d = m.get("domain")
            if d in by_domain:
                by_domain[d] += 1
    except Exception:
        pass
    return {"total_chunks": count(), "by_domain": by_domain}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    prep = prepare(req.question, req.domain, req.history)

    def event_stream():
        # 1) 元信息：领域（是否自动识别）
        yield _sse({"type": "meta", "domain": prep["domain"],
                    "domain_label": prep["domain_label"], "auto": prep["auto"]})
        # 2) 引用来源（检索结果，问答前展示）
        sources = build_sources(prep["chunks"])
        yield _sse({"type": "sources", "sources": sources})
        # 3) 流式正文
        full = []
        for delta in answer_stream(req.question, req.domain, req.history):
            full.append(delta)
            yield _sse({"type": "delta", "content": delta})
        # 4) 结束
        yield _sse({"type": "done", "answer": "".join(full), "sources": sources})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    domain: str = Form(config.DEFAULT_DOMAIN),
):
    data = await file.read()
    if not data:
        return {"status": "error", "msg": "空文件"}
    n = ingest_bytes(file.filename, data, domain)
    return {"status": "ok", "source": file.filename, "chunks": n, "domain": domain}

"""FastAPI 主应用：智慧工地 AI 客服后端。

接口：
  对话：  POST /api/chat          SSE 流式问答（自动落库会话）
  元信息：GET  /api/health        健康检查
          GET  /api/domains       4 大领域
          GET  /api/stats         知识库统计
  知识库：POST /api/upload         文档上传 + 自动索引
          POST /api/preview-chunks 切片预览（不入库）
          GET  /api/documents      已上传文档列表
          DELETE /api/documents/{source} 删除文档（含向量）
  历史：  GET  /api/conversations  会话列表
          GET  /api/conversations/{id} 会话详情
          DELETE /api/conversations/{id} 删除会话
  评价：  POST /api/feedback       提交评价（低分自动进 badcase）
          GET  /api/feedbacks      评价列表
  Badcase:GET  /api/badcases       坏例列表
          PATCH /api/badcases/{id} 标记状态/原因
"""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from . import config
from .rag import answer_stream, build_sources, prepare
from .ingest import ingest_bytes, chunk_text, parse_file
from .store import count, backend_name, get_metadatas, delete_by_source
from .seed import ensure_seed
from . import data_store
from .schemas import ChatRequest, FeedbackRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_seed()
    data_store._seed()
    yield


app = FastAPI(title="智慧工地 AI 客服", version="1.1.0", lifespan=lifespan)

# 允许前端跨域（前后端分离部署时端口不同）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/")
def root():
    return {"status": "ok", "service": "smart-site-ai-cs"}


@app.get("/api/health")
def health():
    try:
        n = count()
    except Exception:
        n = -1
    return {
        "status": "ok",
        "chunks": n,
        "has_key": bool(config.DASHSCOPE_API_KEY),
        "backend": backend_name(),
    }


@app.get("/api/domains")
def domains():
    return {"domains": [{"key": k, "label": v} for k, v in config.DOMAINS.items()]}


@app.get("/api/stats")
def stats():
    by_domain = {k: 0 for k in config.VALID_DOMAINS}
    try:
        for m in get_metadatas():
            d = m.get("domain")
            if d in by_domain:
                by_domain[d] += 1
    except Exception:
        pass
    try:
        total = count()
    except Exception:
        total = 0
    return {"total_chunks": total, "by_domain": by_domain}


# ---------------------- 对话（SSE，自动落库会话） ----------------------
@app.post("/api/chat")
async def chat(req: ChatRequest):
    prep = prepare(req.question, req.domain, req.history)

    def event_stream():
        yield _sse({"type": "meta", "domain": prep["domain"],
                    "domain_label": prep["domain_label"], "auto": prep["auto"]})
        sources = build_sources(prep["chunks"])
        yield _sse({"type": "sources", "sources": sources})
        full = []
        try:
            for delta in answer_stream(req.question, req.domain, req.history):
                full.append(delta)
                yield _sse({"type": "delta", "content": delta})
        except Exception as e:  # 模型调用异常：优雅提示，不中断流
            tail = f"\n\n[回答生成中断：{e}]"
            full.append(tail)
            yield _sse({"type": "delta", "content": tail})

        answer = "".join(full)
        yield _sse({"type": "done", "answer": answer, "sources": sources})

        # 落库会话（含本轮问答），供历史/评价/badcase 使用
        try:
            messages = (req.history or []) + [
                {"role": "user", "content": req.question},
                {"role": "ai", "content": answer, "sources": sources},
            ]
            data_store.save_conversation(
                domain=prep["domain"],
                domain_label=prep["domain_label"],
                messages=messages,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("会话落库失败: %s", e)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------- 知识库：上传 + 索引 ----------------------
@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    domain: str = Form(config.DEFAULT_DOMAIN),
):
    data = await file.read()
    if not data:
        return JSONResponse({"status": "error", "msg": "空文件"}, status_code=400)
    n = ingest_bytes(file.filename, data, domain)
    data_store.upsert_document(
        source=file.filename, filename=file.filename, domain=domain, chunks=n)
    return {"status": "ok", "source": file.filename, "chunks": n, "domain": domain}


@app.post("/api/preview-chunks")
async def preview_chunks(
    file: UploadFile = File(...),
    domain: str = Form(config.DEFAULT_DOMAIN),
):
    """切片预览：解析 + 切分，但不写向量库。返回切片明细（含字符数、来源、章节）。"""
    data = await file.read()
    if not data:
        return JSONResponse({"status": "error", "msg": "空文件"}, status_code=400)
    try:
        text = parse_file(file.filename, data)
    except Exception as e:
        return JSONResponse({"status": "error", "msg": f"解析失败: {e}"}, status_code=400)
    chunks = chunk_text(text, file.filename, domain)
    preview = [{
        "index": i + 1,
        "text": c["text"],
        "length": len(c["text"]),
        "section": c["metadata"].get("section", ""),
    } for i, c in enumerate(chunks)]
    return {
        "status": "ok",
        "source": file.filename,
        "domain": domain,
        "plain_length": len(text),
        "chunk_count": len(chunks),
        "chunks": preview,
    }


@app.get("/api/documents")
def documents():
    return {"documents": data_store.list_documents()}


@app.delete("/api/documents/{source:path}")
def delete_document(source: str):
    # 同步删除向量库切片
    try:
        delete_by_source(source)
    except Exception:
        pass
    ok = data_store.delete_document(source)
    return {"status": "ok" if ok else "not_found", "source": source}


# ---------------------- 历史对话 ----------------------
@app.get("/api/conversations")
def conversations(domain: str = Query(None), limit: int = Query(100)):
    return {"conversations": data_store.list_conversations(limit=limit, domain=domain)}


@app.get("/api/conversations/{conv_id}")
def conversation_detail(conv_id: str):
    conv = data_store.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


@app.delete("/api/conversations/{conv_id}")
def conversation_delete(conv_id: str):
    ok = data_store.delete_conversation(conv_id)
    return {"status": "ok" if ok else "not_found", "id": conv_id}


# ---------------------- 用户评价 ----------------------
@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    fb = data_store.add_feedback(req.conv_id, req.rating, req.comment or "")
    return {"status": "ok", "feedback": fb}


@app.get("/api/feedbacks")
def feedbacks(limit: int = Query(200)):
    return {"feedbacks": data_store.list_feedbacks(limit=limit)}


# ---------------------- Badcase 分析 ----------------------
@app.get("/api/badcases")
def badcases(status: str = Query(None), limit: int = Query(200)):
    return {"badcases": data_store.list_badcases(status=status, limit=limit)}


@app.patch("/api/badcases/{bc_id}")
async def badcase_update(bc_id: str, status: str = Form(None), reason: str = Form(None)):
    bc = data_store.update_badcase(bc_id, status=status, reason=reason)
    if not bc:
        raise HTTPException(status_code=404, detail="badcase 不存在")
    return {"status": "ok", "badcase": bc}

"""向量库封装。

优先使用 Chroma（生产/Docker）。若环境无法编译 chroma-hnswlib（如缺少 C++ 工具链的
本地 macOS），自动降级到纯 numpy 的内存向量库，保证接口与逻辑可本地验证。
API 对外一致：add_chunks / query / count / delete_by_source / get_metadatas。
"""
import uuid
from . import config

try:
    import chromadb  # noqa
    from chromadb.config import Settings
    _HAS_CHROMA = True
except Exception:
    _HAS_CHROMA = False


# ---------------- Chroma 实现 ----------------
_chroma_client = None
_chroma_collection = None


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_DIR,
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
        )
    return _chroma_client


def _chroma_collection():
    global _chroma_collection
    if _chroma_collection is None:
        _chroma_collection = _get_client().get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection


# ---------------- 内存兜底实现（纯 numpy） ----------------
class _MemStore:
    def __init__(self):
        self.ids = []
        self.docs = []
        self.embs = []   # list of np.array
        self.metas = []

    def reset(self):
        self.ids, self.docs, self.embs, self.metas = [], [], [], []

    def add(self, ids, documents, embeddings, metadatas):
        import numpy as np
        for i, d, e, m in zip(ids, documents, embeddings, metadatas):
            if i in self.ids:
                idx = self.ids.index(i)
                self.docs[idx], self.embs[idx], self.metas[idx] = d, np.array(e), m
            else:
                self.ids.append(i)
                self.docs.append(d)
                self.embs.append(np.array(e))
                self.metas.append(m)

    def count(self):
        return len(self.ids)

    def delete(self, where=None):
        if not where:
            self.reset()
            return
        keep = [i for i, m in enumerate(self.metas) if m.get("source") != where.get("source")]
        self.ids = [self.ids[i] for i in keep]
        self.docs = [self.docs[i] for i in keep]
        self.embs = [self.embs[i] for i in keep]
        self.metas = [self.metas[i] for i in keep]

    def get(self, include=None):
        return {"ids": self.ids, "documents": self.docs, "metadatas": self.metas}

    def query(self, query_embeddings, n_results=5, where=None, include=None):
        import numpy as np
        q = np.array(query_embeddings[0])
        out_d, out_m, out_dist = [], [], []
        for d, e, m in zip(self.docs, self.embs, self.metas):
            if where and m.get("domain") != where.get("domain"):
                continue
            sim = float(np.dot(q, e) / (np.linalg.norm(q) * np.linalg.norm(e) + 1e-9))
            out_d.append(d)
            out_m.append(m)
            out_dist.append(1.0 - sim)
        order = sorted(range(len(out_dist)), key=lambda i: out_dist[i])
        k = min(n_results, len(order))
        order = order[:k]
        return {
            "documents": [[out_d[i] for i in order]],
            "metadatas": [[out_m[i] for i in order]],
            "distances": [[out_dist[i] for i in order]],
        }


_mem = None


def _get_mem():
    global _mem
    if _mem is None:
        _mem = _MemStore()
    return _mem


# ---------------- 统一对外接口 ----------------
# 默认内存向量库（零外部依赖，容器内 100% 稳定）。
# 仅当 VECTOR_BACKEND=chroma 且 chroma 依赖可用时启用 Chroma 持久化。
_USE_CHROMA = _HAS_CHROMA and getattr(config, "VECTOR_BACKEND", "memory") == "chroma"
_chroma_failed = False
import logging as _logging


def _backend():
    return "chroma" if (_USE_CHROMA and not _chroma_failed) else "memory"


def _run(op, *args, **kwargs):
    """执行向量库操作；chroma 模式下异常则降级内存库重试一次。"""
    global _chroma_failed
    if _USE_CHROMA and not _chroma_failed:
        try:
            return op(_chroma_collection(), *args, **kwargs)
        except Exception as e:
            _logging.getLogger(__name__).warning(
                "Chroma 操作失败，降级到内存向量库: %s", e
            )
            _chroma_failed = True
            return op(_get_mem(), *args, **kwargs)
    return op(_get_mem(), *args, **kwargs)


def count() -> int:
    return _run(lambda c: c.count())


def add_chunks(chunks: list[dict]) -> int:
    if not chunks:
        return 0
    from .embed import embed_texts
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    _run(lambda c: c.add(
        ids=[c["id"] for c in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[c["metadata"] for c in chunks],
    ))
    return len(chunks)


def query(text: str, domain: str | None = None, top_k: int = None) -> list[dict]:
    top_k = top_k or config.TOP_K
    from .embed import embed_texts
    q_emb = embed_texts([text])[0]
    where = {"domain": domain} if domain and domain in config.VALID_DOMAINS else None
    res = _run(lambda c: c.query(
        query_embeddings=[q_emb],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    ))
    out = []
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    for d, m, dist in zip(docs, metas, dists):
        sim = 1.0 - float(dist)
        out.append({"text": d, "score": round(sim, 4), "metadata": m})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def delete_by_source(source: str):
    try:
        _run(lambda c: c.delete(where={"source": source}))
    except Exception:
        pass


def get_metadatas() -> list:
    return _run(lambda c: c.get(include=["metadatas"]).get("metadatas", []))


def backend_name() -> str:
    return _backend()

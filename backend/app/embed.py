"""Embedding 客户端：DashScope text-embedding-v3，OpenAI 兼容。

统一维度 EMBED_DIM（默认 1024），与 Chroma 集合维度严格一致。
"""
from . import config
from .llm import client


def embed_texts(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    """批量向量化，自动分批避免超 API 上限/超时。空列表直接返回空。"""
    if not texts:
        return []
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = client().embeddings.create(
            model=config.EMBED_MODEL,
            input=batch,
            dimensions=config.EMBED_DIM,
        )
        # 按输入顺序对齐
        ordered = sorted(resp.data, key=lambda d: d.index)
        out.extend(d.embedding for d in ordered)
    return out

"""请求/响应数据模型。"""
from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    domain: Optional[str] = None          # 用户主动选择的领域；为空则自动识别
    history: Optional[list[dict]] = None  # 多轮上下文：[{"role","content"}]


class SourceItem(BaseModel):
    text: str
    score: float
    source: str
    section: str = ""
    domain: str = ""


class ChatDone(BaseModel):
    answer: str
    domain: str
    sources: list[SourceItem]
    auto_domain: bool = False


class UploadResponse(BaseModel):
    source: str
    chunks: int
    domain: str
    status: str = "ok"


class StatsResponse(BaseModel):
    total_chunks: int
    by_domain: dict

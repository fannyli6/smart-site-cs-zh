"""轻量内存数据层：会话历史 / 用户评价 / Badcase / 文档管理。

说明：
- 纯内存字典存储，进程重启即清空（练手/演示足够，零外部依赖）。
- 生产可替换为 SQLite/Postgres；对外接口保持稳定，仅改本文件实现即可。
- 启动时 seed 少量示例数据，便于前端直接看到非空状态。
"""
import time
import uuid
from typing import Optional

# ---------------------- 存储 ----------------------
_conversations: dict[str, dict] = {}   # id -> {id, domain, domain_label, messages[], created_at, feedback}
_feedbacks: dict[str, dict] = {}      # id -> {id, conv_id, rating, comment, created_at}
_badcases: dict[str, dict] = {}       # id -> {id, conv_id, question, answer, domain, reason, status, created_at}
_documents: dict[str, dict] = {}      # source -> {source, filename, domain, chunks, created_at}

_LOCK = __import__("threading").Lock()


def _now() -> float:
    return time.time()


def _seed():
    if _conversations:
        return
    sample = [
        {
            "domain": "device_fault",
            "domain_label": "设备故障",
            "question": "温湿度传感器一直掉线怎么办？",
            "answer": "请依次排查：1）检查供电与网线接头是否松动；2）确认网关在线且传感器在白名单内；3）查看设备日志是否有频繁重连。若仍掉线，多为信号干扰或模块损坏，建议更换安装点位或模块。",
            "rating": 5,
            "feedback_comment": "很准，按步骤排查解决了。",
        },
        {
            "domain": "installation",
            "domain_label": "安装实施",
            "question": "摄像头立杆基础浇筑有什么要求？",
            "answer": "立杆基础一般要求 C25 混凝土、深度≥1.2m、预埋件居中；养护≥7 天方可立杆，回填需分层夯实。具体以现场岩土条件与设计图纸为准。",
            "rating": 2,
            "feedback_comment": "回答太笼统，没给本地化参数。",
        },
        {
            "domain": "gov_integration",
            "domain_label": "对接政府平台",
            "question": "住建局实名制平台对接需要哪些字段？",
            "answer": "需推送人员实名信息（姓名、身份证、工种、班组、进退场时间）、考勤数据；接口需按当地平台规范做签名与定时上报。建议先对接联调环境确认字段映射。",
            "rating": 4,
            "feedback_comment": "",
        },
    ]
    for s in sample:
        conv_id = str(uuid.uuid4())
        _conversations[conv_id] = {
            "id": conv_id,
            "domain": s["domain"],
            "domain_label": s["domain_label"],
            "messages": [
                {"role": "user", "content": s["question"]},
                {"role": "ai", "content": s["answer"], "sources": []},
            ],
            "created_at": _now(),
            "feedback": None,
        }
        if s["rating"] is not None:
            fb_id = str(uuid.uuid4())
            _feedbacks[fb_id] = {
                "id": fb_id,
                "conv_id": conv_id,
                "rating": s["rating"],
                "comment": s["feedback_comment"],
                "created_at": _now(),
            }
            _conversations[conv_id]["feedback"] = {
                "rating": s["rating"], "comment": s["feedback_comment"]}
        # 评分<=2 自动进入 badcase
        if s["rating"] is not None and s["rating"] <= 2:
            bc_id = str(uuid.uuid4())
            _badcases[bc_id] = {
                "id": bc_id,
                "conv_id": conv_id,
                "question": s["question"],
                "answer": s["answer"],
                "domain": s["domain"],
                "reason": "用户评分较低（%d/5）" % s["rating"],
                "status": "pending",
                "created_at": _now(),
            }


# ---------------------- 会话 ----------------------
def save_conversation(domain: str, domain_label: str, messages: list[dict],
                      feedback: Optional[dict] = None) -> dict:
    with _LOCK:
        _seed()
        cid = str(uuid.uuid4())
        conv = {
            "id": cid,
            "domain": domain,
            "domain_label": domain_label,
            "messages": messages,
            "created_at": _now(),
            "feedback": feedback,
        }
        _conversations[cid] = conv
        return conv


def list_conversations(limit: int = 100, domain: Optional[str] = None) -> list[dict]:
    with _LOCK:
        _seed()
        items = list(_conversations.values())
        if domain:
            items = [c for c in items if c["domain"] == domain]
        items.sort(key=lambda c: c["created_at"], reverse=True)
        return items[:limit]


def get_conversation(conv_id: str) -> Optional[dict]:
    with _LOCK:
        return _conversations.get(conv_id)


def delete_conversation(conv_id: str) -> bool:
    with _LOCK:
        return _conversations.pop(conv_id, None) is not None


# ---------------------- 评价 ----------------------
def add_feedback(conv_id: str, rating: int, comment: str = "") -> dict:
    with _LOCK:
        _seed()
        fid = str(uuid.uuid4())
        fb = {
            "id": fid,
            "conv_id": conv_id,
            "rating": rating,
            "comment": comment or "",
            "created_at": _now(),
        }
        _feedbacks[fid] = fb
        conv = _conversations.get(conv_id)
        if conv:
            conv["feedback"] = {"rating": rating, "comment": fb["comment"]}
            # 低分自动进 badcase
            if rating <= 2:
                bc_id = str(uuid.uuid4())
                msgs = conv.get("messages", [])
                q = next((m["content"] for m in msgs if m["role"] == "user"), "")
                a = next((m["content"] for m in msgs if m["role"] == "ai"), "")
                _badcases[bc_id] = {
                    "id": bc_id,
                    "conv_id": conv_id,
                    "question": q,
                    "answer": a,
                    "domain": conv.get("domain", ""),
                    "reason": "用户评分较低（%d/5）" % rating,
                    "status": "pending",
                    "created_at": _now(),
                }
        return fb


def list_feedbacks(limit: int = 200) -> list[dict]:
    with _LOCK:
        _seed()
        items = list(_feedbacks.values())
        items.sort(key=lambda f: f["created_at"], reverse=True)
        return items[:limit]


# ---------------------- Badcase ----------------------
def list_badcases(status: Optional[str] = None, limit: int = 200) -> list[dict]:
    with _LOCK:
        _seed()
        items = list(_badcases.values())
        if status:
            items = [b for b in items if b["status"] == status]
        items.sort(key=lambda b: b["created_at"], reverse=True)
        return items[:limit]


def update_badcase(bc_id: str, status: Optional[str] = None,
                   reason: Optional[str] = None) -> Optional[dict]:
    with _LOCK:
        bc = _badcases.get(bc_id)
        if not bc:
            return None
        if status is not None:
            bc["status"] = status
        if reason is not None:
            bc["reason"] = reason
        return bc


def add_badcase_from_answer(conv_id: str, question: str, answer: str,
                            domain: str, reason: str = "答案疑似不理想") -> dict:
    with _LOCK:
        bc_id = str(uuid.uuid4())
        bc = {
            "id": bc_id,
            "conv_id": conv_id,
            "question": question,
            "answer": answer,
            "domain": domain,
            "reason": reason,
            "status": "pending",
            "created_at": _now(),
        }
        _badcases[bc_id] = bc
        return bc


# ---------------------- 文档管理 ----------------------
def upsert_document(source: str, filename: str, domain: str, chunks: int) -> dict:
    with _LOCK:
        doc = {
            "source": source,
            "filename": filename,
            "domain": domain,
            "chunks": chunks,
            "created_at": _now(),
        }
        _documents[source] = doc
        return doc


def list_documents() -> list[dict]:
    with _LOCK:
        items = list(_documents.values())
        items.sort(key=lambda d: d["created_at"], reverse=True)
        return items


def delete_document(source: str) -> bool:
    with _LOCK:
        return _documents.pop(source, None) is not None

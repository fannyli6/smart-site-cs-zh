"""开机自动灌入种子知识库（仅当库为空时）。"""
from . import config
from .ingest import ingest_markdown_string
from .seed_data import SEED_DOCS
from .store import count
from .llm import has_key


def ensure_seed():
    if not has_key():
        # 无 API Key 无法向量化，跳过；配置 Key 后重启自动灌入
        print("[seed] 未配置 DASHSCOPE_API_KEY，跳过种子灌库（配置后重启自动灌入）")
        return
    if count() > 0:
        return
    total = 0
    for title, domain, text in SEED_DOCS:
        total += ingest_markdown_string(title, text, domain)
    print(f"[seed] 已灌入种子知识 {total} 个切片")

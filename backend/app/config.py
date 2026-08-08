"""全局配置：全部通过环境变量注入，便于 Sealos / 容器部署。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

# ---------- 大模型 / Embedding（阿里云百炼 DashScope，OpenAI 兼容） ----------
# 文档要求 Qwen 私有部署；云端部署使用 DashScope 的 OpenAI 兼容接口，行为一致。
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
# 对话模型：默认 qwen-plus（性价比高）；可改 qwen-max / qwen-turbo / qwen2.5-7b-instruct
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen-plus")
# 嵌入模型：text-embedding-v3，维度 1024（与 Chroma 集合维度必须一致）
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-v3")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

# ---------- 向量库 ----------
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "smart_site_kb")

# ---------- 检索参数 ----------
TOP_K = int(os.getenv("TOP_K", "5"))          # 召回候选数量
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.30"))  # 相似度下限，低于则判为"答不出"
CONTEXT_MAX_CHUNKS = int(os.getenv("CONTEXT_MAX_CHUNKS", "4"))  # 进入 Prompt 的最大片段数

# ---------- 4 大业务领域 ----------
DOMAINS = {
    "device_fault": "设备故障",
    "installation": "安装实施",
    "data_anomaly": "平台数据异常",
    "gov_integration": "对接政府平台",
}
DEFAULT_DOMAIN = "device_fault"

# 未选领域时，要求 LLM 自动归类；返回值必须是以下 key 之一或 "unknown"
VALID_DOMAINS = list(DOMAINS.keys())

# ---------- 服务 ----------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

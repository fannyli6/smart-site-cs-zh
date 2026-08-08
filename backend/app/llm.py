"""LLM 客户端：基于阿里云百炼 DashScope 的 OpenAI 兼容接口。

文档要求 Qwen 私有部署；云端部署走 DashScope 兼容模式，模型行为一致。
若未配置 DASHSCOPE_API_KEY，提供清晰的错误提示，便于部署时自查。
"""
from openai import OpenAI

from . import config

_client = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.DASHSCOPE_API_KEY or "EMPTY",
            base_url=config.OPENAI_BASE_URL,
        )
    return _client


def has_key() -> bool:
    return bool(config.DASHSCOPE_API_KEY)


def chat(messages: list[dict], stream: bool = True, temperature: float = 0.3):
    """普通对话。messages 为 [{"role","content"}] 列表。"""
    return client().chat.completions.create(
        model=config.CHAT_MODEL,
        messages=messages,
        stream=stream,
        temperature=temperature,
    )


def complete(prompt: str, stream: bool = True, temperature: float = 0.2):
    """单轮补全（用于意图识别等内部任务）。"""
    return chat([{"role": "user", "content": prompt}], stream=stream, temperature=temperature)

"""领域意图识别：未显式选择领域时，判断问题归属。

优先用 LLM 分类；无 API key 时退化为关键词匹配，保证离线可用。
"""
from . import config
from .llm import chat, has_key

_DOMAIN_HINTS = {
    "device_fault": ["掉线", "离线", "故障", "坏了", "异常", "花屏", "不开门", "无反应",
                      "传感器", "摄像头", "闸机", "读卡", "显示屏", "广播", "重启", "更换", "卡死"],
    "installation": ["安装", "部署", "勘测", "高度", "布线", "规范", "验收", "施工", "方案", "调试"],
    "data_anomaly": ["数据", "上报", "缺失", "断档", "恒值", "跳变", "告警", "误报", "补录", "推送失败", "阈值"],
    "gov_integration": ["住建局", "政府", "监管", "对接", "上报地址", "appkey", "secret", "字段映射", "回执"],
}


def detect_domain(question: str) -> str:
    """返回领域 key 或 'unknown'。"""
    q = question.strip()
    if has_key():
        try:
            prompt = (
                "你是智慧工地客服系统的意图分类器。请将用户问题归类到以下四类之一，"
                "只返回一个 key，不要解释：\n"
                "device_fault（设备故障）\n"
                "installation（安装实施）\n"
                "data_anomaly（平台数据异常）\n"
                "gov_integration（对接政府平台）\n"
                "unknown（与以上均无关）\n\n"
                f"用户问题：{q}\n分类 key："
            )
            resp = chat([{"role": "user", "content": prompt}], stream=False, temperature=0)
            key = resp.choices[0].message.content.strip().lower()
            key = key.strip("`. \n")
            if key in config.VALID_DOMAINS:
                return key
            return "unknown"
        except Exception:
            pass
    # 关键词退化策略
    scores = {d: 0 for d in config.VALID_DOMAINS}
    for d, words in _DOMAIN_HINTS.items():
        for w in words:
            if w in q:
                scores[d] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"

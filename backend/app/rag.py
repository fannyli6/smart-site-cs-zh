"""RAG 检索 + 生成。

流程：向量检索 -> 取高相似度片段 -> 拼装带领域约束的 Prompt -> LLM 流式生成。
要求：基于知识库事实、给出可操作步骤、标注来源；答不出时引导人工。
"""
from . import config
from .intent import detect_domain
from .llm import chat, has_key
from .store import query


def retrieve(question: str, domain: str | None):
    """检索并返回进入上下文的片段列表（已按阈值过滤）。"""
    results = query(question, domain=domain, top_k=config.TOP_K)
    kept = [r for r in results if r["score"] >= config.SCORE_THRESHOLD]
    return kept[: config.CONTEXT_MAX_CHUNKS], results


def _build_prompt(question: str, chunks: list[dict], domain_label: str, history: list[dict]):
    ctx = ""
    for i, c in enumerate(chunks, 1):
        src = c["metadata"].get("source", "未知")
        sec = c["metadata"].get("section", "")
        ctx += f"\n【参考片段{i}】来源：《{src}》{(' / ' + sec) if sec else ''}\n{c['text']}\n"

    sys = (
        f"你是「智慧工地 AI 客服」，专门解答智慧工地领域（当前问题属于：{domain_label}）的专业问题。\n"
        "严格遵守以下规则：\n"
        "1. 只依据下方【参考片段】中的事实回答，不允许编造知识库以外的内容。\n"
        "2. 回答要具体、有操作性：给出可执行的排查/处理步骤（如 1.检查XX 2.尝试XX 3.否则XX）。\n"
        "3. 必须说明可能原因，帮助用户理解问题。\n"
        "4. 回答末尾用「参考来源」列出引用（文档名+章节），格式：参考来源：《文档名》章节。\n"
        "5. 如果参考片段不足以回答，明确说明「知识库暂未覆盖该问题，建议联系人工客服」，"
        "不要强行编造；可给出通用排查思路但须注明非官方结论。\n"
        "6. 不闲聊，聚焦问题本身。\n"
    )
    messages = [{"role": "system", "content": sys}]
    if history:
        for h in history[-6:]:
            if h.get("role") in ("user", "assistant"):
                messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": f"{question}\n\n{ctx}"})
    return messages


def prepare(question: str, domain: str | None, history: list[dict] = None):
    """准备阶段：解析领域、检索片段、拼装 Prompt。返回供 SSE 使用的上下文。"""
    auto = False
    if not domain or domain not in config.VALID_DOMAINS:
        domain = detect_domain(question)
        auto = True
    domain_label = config.DOMAINS.get(domain, "综合")
    # 未配置 Key 时跳过检索（无 Embedding 可用），直接走友好提示
    chunks = []
    if has_key():
        chunks, _ = retrieve(question, domain if domain != "unknown" else None)
    messages = _build_prompt(question, chunks, domain_label, history or [])
    return {
        "domain": domain,
        "domain_label": domain_label,
        "auto": auto,
        "chunks": chunks,
        "messages": messages,
    }


def answer_stream(question: str, domain: str | None, history: list[dict] = None):
    """生成器：逐个 yield 文本片段（delta）。无 key 时 yield 友好提示。"""
    if not has_key():
        yield ("⚠️ 未配置 DASHSCOPE_API_KEY，AI 无法生成回答。\n"
               "请在环境变量中配置后重启服务（Sealos 部署时在环境变量里填写）。")
        return
    prep = prepare(question, domain, history)
    try:
        resp = chat(prep["messages"], stream=True, temperature=0.3)
        for part in resp:
            if not part.choices:
                continue
            delta = part.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as e:
        yield f"\n[生成失败] {e}"


def build_sources(chunks: list[dict]) -> list[dict]:
    out = []
    for c in chunks:
        out.append({
            "text": c["text"],
            "score": c["score"],
            "source": c["metadata"].get("source", ""),
            "section": c["metadata"].get("section", ""),
            "domain": c["metadata"].get("domain", ""),
        })
    return out


def resolve_domain(question: str, domain: str | None):
    """供接口层复用：返回 (domain, auto)。"""
    auto = False
    if not domain or domain not in config.VALID_DOMAINS:
        domain = detect_domain(question)
        auto = True
    return domain, auto

// 前端 API 封装：领域、统计、文档上传、SSE 流式问答

export async function getDomains() {
  const r = await fetch('/api/domains')
  const d = await r.json()
  return d.domains || []
}

export async function getStats() {
  const r = await fetch('/api/stats')
  return r.json()
}

export async function uploadDoc(file, domain) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('domain', domain)
  const r = await fetch('/api/upload', { method: 'POST', body: fd })
  return r.json()
}

// SSE 流式问答。onEvent 收到每个解析后的事件对象。
export async function chatStream({ question, domain, history }, onEvent) {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, domain: domain || null, history: history || [] }),
  })
  if (!resp.ok) throw new Error('请求失败 ' + resp.status)
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    // 按 SSE 事件边界切分
    let idx
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      const payload = line.slice(5).trim()
      if (!payload) continue
      try {
        onEvent(JSON.parse(payload))
      } catch (e) {
        /* ignore malformed */
      }
    }
  }
}

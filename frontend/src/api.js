// 前端 API 封装：领域、统计、文档上传、SSE 流式问答，及新增的
// 会话历史 / 用户评价 / badcase / 知识库切分预览 / 文档管理

const API = '/api'

export async function getDomains() {
  const r = await fetch(`${API}/domains`)
  const d = await r.json()
  return d.domains || []
}

export async function getStats() {
  const r = await fetch(`${API}/stats`)
  return r.json()
}

export async function uploadDoc(file, domain) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('domain', domain)
  const r = await fetch(`${API}/upload`, { method: 'POST', body: fd })
  return r.json()
}

// 切片预览（不入库）
export async function previewChunks(file, domain) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('domain', domain)
  const r = await fetch(`${API}/preview-chunks`, { method: 'POST', body: fd })
  return r.json()
}

export async function getDocuments() {
  const r = await fetch(`${API}/documents`)
  return (await r.json()).documents || []
}

export async function deleteDocument(source) {
  const r = await fetch(`${API}/documents/${encodeURIComponent(source)}`, { method: 'DELETE' })
  return r.json()
}

// 会话历史
export async function getConversations(domain = '', limit = 100) {
  const qs = new URLSearchParams()
  if (domain) qs.set('domain', domain)
  qs.set('limit', String(limit))
  const r = await fetch(`${API}/conversations?${qs.toString()}`)
  return (await r.json()).conversations || []
}

export async function getConversation(id) {
  const r = await fetch(`${API}/conversations/${id}`)
  return r.json()
}

export async function deleteConversation(id) {
  const r = await fetch(`${API}/conversations/${id}`, { method: 'DELETE' })
  return r.json()
}

// 用户评价
export async function submitFeedback(convId, rating, comment = '') {
  const r = await fetch(`${API}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conv_id: convId, rating, comment }),
  })
  return r.json()
}

export async function getFeedbacks(limit = 200) {
  const r = await fetch(`${API}/feedbacks?limit=${limit}`)
  return (await r.json()).feedbacks || []
}

// badcase
export async function getBadcases(status = '', limit = 200) {
  const qs = new URLSearchParams()
  if (status) qs.set('status', status)
  qs.set('limit', String(limit))
  const r = await fetch(`${API}/badcases?${qs.toString()}`)
  return (await r.json()).badcases || []
}

export async function updateBadcase(id, status, reason) {
  const fd = new FormData()
  if (status) fd.append('status', status)
  if (reason != null) fd.append('reason', reason)
  const r = await fetch(`${API}/badcases/${id}`, { method: 'PATCH', body: fd })
  return r.json()
}

// SSE 流式问答。onEvent 收到每个解析后的事件对象。
export async function chatStream({ question, domain, history }, onEvent) {
  const resp = await fetch(`${API}/chat`, {
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

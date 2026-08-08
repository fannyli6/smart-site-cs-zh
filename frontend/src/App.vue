<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { getDomains, getStats, uploadDoc, chatStream } from './api.js'

const domains = ref([])
const selectedDomain = ref(null) // null = 自动识别
const messages = ref([])
const input = ref('')
const loading = ref(false)
const stats = ref({ total_chunks: 0, by_domain: {} })

const showUpload = ref(false)
const uploadFile = ref(null)
const uploadDomain = ref('device_fault')
const uploading = ref(false)
const uploadMsg = ref('')

const listRef = ref(null)

onMounted(async () => {
  domains.value = await getDomains()
  try { stats.value = await getStats() } catch (e) {}
})

async function scrollToBottom() {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
}

function pickDomain(key) {
  selectedDomain.value = selectedDomain.value === key ? null : key
}

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: q })
  const aiMsg = { role: 'ai', content: '', sources: [], domainLabel: '', auto: false, streaming: true }
  messages.value.push(aiMsg)
  loading.value = true
  scrollToBottom()

  const history = messages.value
    .filter((m) => m.role === 'user' || (m.role === 'ai' && m.content))
    .slice(-8)
    .map((m) => ({ role: m.role, content: m.content }))

  // 当前这条 ai 消息在数组中的引用（用 find 定位最后一条 ai）
  const target = () => messages.value[messages.value.length - 1]

  try {
    await chatStream({ question: q, domain: selectedDomain.value, history }, (ev) => {
      const m = target()
      if (ev.type === 'meta') {
        m.domainLabel = ev.domain_label
        m.auto = ev.auto
      } else if (ev.type === 'sources') {
        m.sources = ev.sources || []
      } else if (ev.type === 'delta') {
        m.content += ev.content
        scrollToBottom()
      } else if (ev.type === 'done') {
        m.content = ev.answer
        m.sources = ev.sources || []
        m.streaming = false
      }
    })
  } catch (e) {
    target().content += '\n[连接错误] ' + e.message
    target().streaming = false
  } finally {
    target().streaming = false
    loading.value = false
    scrollToBottom()
    try { stats.value = await getStats() } catch (e) {}
  }
}

function onEnter(e) {
  if (e.shiftKey) return // Shift+Enter 换行
  e.preventDefault()
  send()
}

async function doUpload() {
  if (!uploadFile.value) { uploadMsg.value = '请先选择文件'; return }
  uploading.value = true
  uploadMsg.value = '上传并索引中…'
  try {
    const r = await uploadDoc(uploadFile.value, uploadDomain.value)
    uploadMsg.value = r.status === 'ok'
      ? `✅ 已索引《${r.source}》${r.chunks} 个切片`
      : '❌ ' + (r.msg || '上传失败')
    if (r.status === 'ok') stats.value = await getStats()
  } catch (e) {
    uploadMsg.value = '❌ ' + e.message
  } finally {
    uploading.value = false
  }
}

const quickQuestions = [
  '温湿度传感器一直掉线怎么办？',
  'PM2.5 数值一直是 9999 是怎么回事？',
  '摄像头画面花屏卡顿怎么办？',
  '人脸识别闸机不开门怎么办？',
]
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="title">
        <span class="logo">🏗️</span>
        <div>
          <div class="t1">智慧工地 AI 客服</div>
          <div class="t2">基于知识库的专业答疑 · 数据私有</div>
        </div>
      </div>
      <div class="ops">
        <span class="stat">知识库 {{ stats.total_chunks }} 切片</span>
        <button class="ghost" @click="showUpload = !showUpload">📥 上传知识</button>
      </div>
    </header>

    <div v-if="showUpload" class="upload-panel">
      <div class="row">
        <label>领域：</label>
        <select v-model="uploadDomain">
          <option v-for="d in domains" :key="d.key" :value="d.key">{{ d.label }}</option>
        </select>
      </div>
      <div class="row">
        <input type="file" @change="e => uploadFile = e.target.files[0]" accept=".pdf,.docx,.xlsx,.md,.txt" />
      </div>
      <div class="row">
        <button class="primary" :disabled="uploading" @click="doUpload">
          {{ uploading ? '处理中…' : '开始索引' }}
        </button>
        <span class="up-msg">{{ uploadMsg }}</span>
      </div>
      <div class="hint">支持 PDF / Word / Excel / Markdown / TXT，系统自动解析、切片、向量化。</div>
    </div>

    <div class="domains">
      <button
        class="chip"
        :class="{ active: selectedDomain === null }"
        @click="selectedDomain = null"
      >🤖 自动识别</button>
      <button
        v-for="d in domains"
        :key="d.key"
        class="chip"
        :class="{ active: selectedDomain === d.key }"
        @click="pickDomain(d.key)"
      >{{ d.label }}</button>
    </div>

    <div class="messages" ref="listRef">
      <div v-if="messages.length === 0" class="empty">
        <p>👋 你好，我是智慧工地 AI 客服。</p>
        <p class="sub">问我设备故障、安装实施、数据异常或政府平台对接相关问题吧。</p>
        <div class="quicks">
          <button v-for="q in quickQuestions" :key="q" class="quick" @click="input = q; send()">{{ q }}</button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="bubble">
          <div class="meta-line" v-if="m.role === 'ai' && m.domainLabel">
            <span class="tag">{{ m.domainLabel }}</span>
            <span v-if="m.auto" class="auto">自动识别</span>
          </div>
          <div class="content" v-if="m.content">{{ m.content }}</div>
          <div class="content typing" v-else-if="m.streaming">正在思考…</div>

          <div class="sources" v-if="m.role === 'ai' && m.sources && m.sources.length">
            <details>
              <summary>📚 参考来源（{{ m.sources.length }}）</summary>
              <div v-for="(s, si) in m.sources" :key="si" class="src">
                <div class="src-head">
                  《{{ s.source }}》<span v-if="s.section"> / {{ s.section }}</span>
                  <span class="score">相似度 {{ (s.score * 100).toFixed(0) }}%</span>
                </div>
                <div class="src-text">{{ s.text }}</div>
              </div>
            </details>
          </div>
        </div>
      </div>
    </div>

    <div class="inputbar">
      <textarea
        v-model="input"
        rows="1"
        placeholder="描述你的问题，例如：温湿度传感器一直掉线怎么办？"
        @keydown.enter="onEnter"
      ></textarea>
      <button class="send" :disabled="loading" @click="send">发送</button>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 860px;
  margin: 0 auto;
  background: var(--bg);
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
}
.title { display: flex; align-items: center; gap: 10px; }
.logo { font-size: 26px; }
.t1 { font-weight: 700; font-size: 16px; }
.t2 { font-size: 12px; color: var(--text-weak); }
.ops { display: flex; align-items: center; gap: 10px; }
.stat { font-size: 12px; color: var(--text-weak); }
button.ghost {
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text);
}
.upload-panel {
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 12px 14px;
  font-size: 13px;
}
.upload-panel .row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.upload-panel select, .upload-panel input[type=file] { font-size: 13px; }
.up-msg { color: var(--primary); font-size: 13px; }
.hint { color: var(--text-weak); font-size: 12px; }
button.primary {
  background: var(--primary); color: #fff; border: none;
  border-radius: 8px; padding: 7px 14px; font-size: 13px;
}
.domains {
  display: flex; gap: 8px; padding: 10px 14px; overflow-x: auto;
  background: var(--bg);
}
.chip {
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 16px;
  padding: 6px 12px;
  font-size: 13px;
  white-space: nowrap;
  color: var(--text);
}
.chip.active { background: var(--primary); color: #fff; border-color: var(--primary); }

.messages { flex: 1; overflow-y: auto; padding: 14px; }
.empty { text-align: center; color: var(--text-weak); margin-top: 12vh; }
.empty .sub { font-size: 13px; }
.quicks { display: flex; flex-direction: column; gap: 8px; margin-top: 18px; padding: 0 10px; }
.quick {
  border: 1px solid var(--border); background: #fff; border-radius: 10px;
  padding: 10px 12px; font-size: 13px; text-align: left; color: var(--text);
}
.msg { display: flex; margin-bottom: 14px; }
.msg.user { justify-content: flex-end; }
.msg.ai { justify-content: flex-start; }
.bubble {
  max-width: 82%;
  padding: 10px 12px;
  border-radius: var(--radius);
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}
.msg.user .bubble { background: var(--bubble-user); border-top-right-radius: 2px; }
.msg.ai .bubble { background: var(--bubble-ai); border-top-left-radius: 2px; border: 1px solid var(--border); }
.meta-line { margin-bottom: 6px; }
.tag {
  background: var(--primary-soft); color: var(--primary);
  border-radius: 6px; padding: 1px 7px; font-size: 12px; margin-right: 6px;
}
.auto { font-size: 11px; color: var(--text-weak); }
.content { white-space: pre-wrap; word-break: break-word; }
.typing { color: var(--text-weak); }
.sources { margin-top: 8px; border-top: 1px dashed var(--border); padding-top: 6px; }
.sources summary { font-size: 12px; color: var(--text-weak); cursor: pointer; }
.src { margin-top: 6px; padding: 6px 8px; background: #fafbfc; border-radius: 8px; font-size: 12px; }
.src-head { color: var(--primary); margin-bottom: 2px; }
.score { color: var(--text-weak); margin-left: 6px; }
.src-text { color: var(--text-weak); max-height: 120px; overflow: auto; }

.inputbar {
  display: flex; gap: 8px; padding: 10px 12px;
  background: var(--panel); border-top: 1px solid var(--border);
}
.inputbar textarea {
  flex: 1; resize: none; border: 1px solid var(--border); border-radius: 10px;
  padding: 10px; font-size: 14px; max-height: 120px; font-family: inherit; line-height: 1.5;
}
button.send {
  align-self: flex-end;
  background: var(--primary); color: #fff; border: none;
  border-radius: 10px; padding: 10px 18px; font-size: 14px;
}
button.send:disabled { opacity: .5; }

@media (max-width: 600px) {
  .bubble { max-width: 90%; }
  .t2 { display: none; }
}
</style>

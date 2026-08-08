<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { getDomains, chatStream } from '../api.js'

const domains = ref([])
const activeTab = ref('')          // '' = 自动识别
const messages = ref([])
const input = ref('')
const loading = ref(false)
const listRef = ref(null)

const quickQuestions = [
  '温湿度传感器一直掉线怎么办？',
  'PM2.5 数值一直是 9999 是怎么回事？',
  '摄像头画面花屏卡顿怎么办？',
  '人脸识别闸机不开门怎么办？',
  '住建局实名制平台对接需要哪些字段？',
]

onMounted(async () => {
  domains.value = await getDomains()
})

async function scrollToBottom() {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
}

function isDefaultTab() {
  return activeTab.value === ''
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

  const target = () => messages.value[messages.value.length - 1]

  try {
    await chatStream({ question: q, domain: isDefaultTab() ? null : activeTab.value, history }, (ev) => {
      const m = target()
      if (ev.type === 'meta') { m.domainLabel = ev.domain_label; m.auto = ev.auto }
      else if (ev.type === 'sources') { m.sources = ev.sources || [] }
      else if (ev.type === 'delta') { m.content += ev.content; scrollToBottom() }
      else if (ev.type === 'done') { m.content = ev.answer; m.sources = ev.sources || []; m.streaming = false }
    })
  } catch (e) {
    target().content += '\n[连接错误] ' + e.message
    target().streaming = false
  } finally {
    target().streaming = false
    loading.value = false
    scrollToBottom()
  }
}

function onEnter(e) {
  if (e.shiftKey) return
  e.preventDefault()
  send()
}
</script>

<template>
  <div class="chat-wrap card">
    <!-- 意图类型 Tab -->
    <div class="tabs">
      <button class="tab" :class="{ active: isDefaultTab() }" @click="activeTab = ''">
        🤖 自动识别
      </button>
      <button
        v-for="d in domains"
        :key="d.key"
        class="tab"
        :class="{ active: activeTab === d.key }"
        @click="activeTab = d.key"
      >{{ d.label }}</button>
    </div>

    <div class="messages" ref="listRef">
      <div v-if="messages.length === 0" class="empty">
        <p>👋 你好，我是智慧工地 AI 客服。</p>
        <p class="sub">选择上方意图类型，或让系统自动识别后提问。</p>
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
.chat-wrap {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 130px);
  overflow: hidden;
}
.tabs {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
  background: #fafbfe;
}
.tab {
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 16px;
  padding: 6px 14px;
  font-size: 13px;
  white-space: nowrap;
  color: var(--text);
}
.tab.active { background: var(--primary); color: #fff; border-color: var(--primary); }

.messages { flex: 1; overflow-y: auto; padding: 16px; }
.empty { text-align: center; color: var(--text-weak); margin-top: 8vh; }
.empty .sub { font-size: 13px; }
.quicks { display: flex; flex-direction: column; gap: 8px; margin-top: 18px; padding: 0 10px; }
.quick {
  border: 1px solid var(--border); background: #fff; border-radius: 10px;
  padding: 10px 12px; font-size: 13px; text-align: left; color: var(--text);
}
.quick:hover { border-color: var(--primary); color: var(--primary); }

.msg { display: flex; margin-bottom: 14px; }
.msg.user { justify-content: flex-end; }
.msg.ai { justify-content: flex-start; }
.bubble { max-width: 82%; padding: 10px 12px; border-radius: var(--radius); box-shadow: var(--shadow); }
.msg.user .bubble { background: var(--bubble-user); border-top-right-radius: 2px; }
.msg.ai .bubble { background: var(--bubble-ai); border-top-left-radius: 2px; border: 1px solid var(--border); }
.meta-line { margin-bottom: 6px; }
.tag { background: var(--primary-soft); color: var(--primary); border-radius: 6px; padding: 1px 7px; font-size: 12px; margin-right: 6px; }
.auto { font-size: 11px; color: var(--text-weak); }
.content { white-space: pre-wrap; word-break: break-word; line-height: 1.6; }
.typing { color: var(--text-weak); }
.sources { margin-top: 8px; border-top: 1px dashed var(--border); padding-top: 6px; }
.sources summary { font-size: 12px; color: var(--text-weak); cursor: pointer; }
.src { margin-top: 6px; padding: 6px 8px; background: #fafbfc; border-radius: 8px; font-size: 12px; }
.src-head { color: var(--primary); margin-bottom: 2px; }
.score { color: var(--text-weak); margin-left: 6px; }
.src-text { color: var(--text-weak); max-height: 120px; overflow: auto; }

.inputbar { display: flex; gap: 8px; padding: 12px; background: var(--panel); border-top: 1px solid var(--border); }
.inputbar textarea {
  flex: 1; resize: none; border: 1px solid var(--border); border-radius: 10px;
  padding: 10px; font-size: 14px; max-height: 120px; font-family: inherit; line-height: 1.5;
}
button.send {
  align-self: flex-end; background: var(--primary); color: #fff; border: none;
  border-radius: 10px; padding: 10px 18px; font-size: 14px;
}
</style>

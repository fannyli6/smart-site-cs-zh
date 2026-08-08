<script setup>
import { ref, onMounted } from 'vue'
import {
  getDomains, getConversations, getConversation, deleteConversation, submitFeedback,
} from '../api.js'

const domains = ref([])
const convs = ref([])
const filterDomain = ref('')

const detail = ref(null)
const showDetail = ref(false)

const rating = ref(5)
const comment = ref('')
const fbMsg = ref('')

onMounted(loadAll)
async function loadAll() {
  domains.value = await getDomains()
  await loadConvs()
}
async function loadConvs() {
  convs.value = await getConversations(filterDomain.value)
}
async function openDetail(id) {
  detail.value = await getConversation(id)
  showDetail.value = true
  // 预填已有评价
  if (detail.value.feedback) {
    rating.value = detail.value.feedback.rating
    comment.value = detail.value.feedback.comment || ''
  } else {
    rating.value = 5
    comment.value = ''
  }
  fbMsg.value = ''
}
function closeDetail() { showDetail.value = false; detail.value = null }

async function doDelete(id) {
  if (!confirm('确认删除该会话？')) return
  await deleteConversation(id)
  if (showDetail.value && detail.value && detail.value.id === id) closeDetail()
  await loadConvs()
}

async function doFeedback() {
  if (!detail.value) return
  const r = await submitFeedback(detail.value.id, rating.value, comment.value)
  fbMsg.value = r.status === 'ok' ? '✅ 评价已提交' : '❌ 提交失败'
  detail.value.feedback = { rating: rating.value, comment: comment.value }
  await loadConvs()
}

function fmt(ts) {
  const d = new Date(ts * 1000)
  return d.toLocaleString('zh-CN', { hour12: false })
}
function domainLabel(key) {
  const d = domains.value.find(x => x.key === key)
  return d ? d.label : key
}
function firstQuestion(conv) {
  const u = conv.messages.find(m => m.role === 'user')
  return u ? u.content : '(空)'
}
</script>

<template>
  <div class="history">
    <div class="toolbar">
      <select v-model="filterDomain" @change="loadConvs">
        <option value="">全部领域</option>
        <option v-for="d in domains" :key="d.key" :value="d.key">{{ d.label }}</option>
      </select>
      <span class="count">共 {{ convs.length }} 条会话</span>
    </div>

    <div class="grid">
      <div class="card list">
        <div v-if="!convs.length" class="empty">暂无历史对话</div>
        <div
          v-for="c in convs"
          :key="c.id"
          class="item"
          :class="{ active: detail && detail.id === c.id }"
          @click="openDetail(c.id)"
        >
          <div class="item-top">
            <span class="tag">{{ domainLabel(c.domain) }}</span>
            <span class="time">{{ fmt(c.created_at) }}</span>
          </div>
          <div class="q">{{ firstQuestion(c) }}</div>
          <div class="item-foot">
            <span v-if="c.feedback" class="stars">{'★'.repeat(c.feedback.rating)}{'☆'.repeat(5 - c.feedback.rating)}</span>
            <span v-else class="no-fb">未评价</span>
            <button class="btn danger mini" @click.stop="doDelete(c.id)">删除</button>
          </div>
        </div>
      </div>

      <div class="card detail" v-if="showDetail && detail">
        <div class="d-head">
          <span class="tag">{{ domainLabel(detail.domain) }}</span>
          <button class="btn mini" @click="closeDetail">关闭</button>
        </div>
        <div class="msgs">
          <div v-for="(m, i) in detail.messages" :key="i" class="dmsg" :class="m.role">
            <div class="role">{{ m.role === 'user' ? '用户' : 'AI' }}</div>
            <div class="text">{{ m.content }}</div>
          </div>
        </div>

        <div class="fb">
          <div class="fb-title">用户评价</div>
          <div class="stars-pick">
            <span
              v-for="n in 5"
              :key="n"
              class="star"
              :class="{ on: n <= rating }"
              @click="rating = n"
            >★</span>
          </div>
          <textarea v-model="comment" rows="2" placeholder="补充评价（可选）"></textarea>
          <div class="fb-row">
            <button class="btn primary" @click="doFeedback">提交评价</button>
            <span class="fb-msg">{{ fbMsg }}</span>
          </div>
          <div class="hint">评分 ≤ 2 星会自动进入 Badcase 分析。</div>
        </div>
      </div>
      <div class="card detail placeholder" v-else>
        <div class="empty">从左侧选择一条会话查看详情</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.toolbar select { font-size: 13px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border); }
.count { font-size: 13px; color: var(--text-weak); }

.grid { display: grid; grid-template-columns: 360px 1fr; gap: 16px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }

.list { padding: 8px; max-height: calc(100vh - 220px); overflow: auto; }
.item { padding: 10px 12px; border-radius: 8px; cursor: pointer; border: 1px solid transparent; }
.item:hover { background: #fafbff; }
.item.active { background: var(--primary-soft); border-color: var(--primary); }
.item-top { display: flex; justify-content: space-between; align-items: center; }
.time { font-size: 11px; color: var(--text-weak); }
.q { font-size: 13px; margin: 6px 0; color: var(--text); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.item-foot { display: flex; align-items: center; justify-content: space-between; }
.stars { color: var(--warn); font-size: 12px; }
.no-fb { font-size: 12px; color: var(--text-weak); }
.btn.mini { padding: 3px 9px; font-size: 12px; }

.detail { padding: 16px; display: flex; flex-direction: column; max-height: calc(100vh - 220px); }
.detail.placeholder { align-items: center; justify-content: center; }
.d-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.msgs { flex: 1; overflow: auto; padding: 8px 0; }
.dmsg { margin-bottom: 12px; }
.dmsg .role { font-size: 11px; color: var(--text-weak); margin-bottom: 2px; }
.dmsg .text { font-size: 13px; line-height: 1.6; white-space: pre-wrap; padding: 8px 10px; border-radius: 8px; }
.dmsg.user .text { background: var(--bubble-user); }
.dmsg.ai .text { background: #f6f8fc; border: 1px solid var(--border); }

.fb { border-top: 1px dashed var(--border); padding-top: 10px; }
.fb-title { font-weight: 600; font-size: 13px; margin-bottom: 8px; }
.stars-pick { margin-bottom: 8px; }
.star { font-size: 22px; color: #d4d9e4; cursor: pointer; }
.star.on { color: var(--warn); }
.fb textarea { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 8px; font-size: 13px; font-family: inherit; resize: vertical; }
.fb-row { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
.fb-msg { font-size: 13px; color: var(--primary); }
.hint { color: var(--text-weak); font-size: 12px; margin-top: 4px; }
</style>

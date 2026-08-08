<script setup>
import { ref, onMounted, computed } from 'vue'
import { getDomains, getFeedbacks, getConversation } from '../api.js'

const domains = ref([])
const feedbacks = ref([])
const detail = ref(null)

onMounted(loadAll)
async function loadAll() {
  domains.value = await getDomains()
  feedbacks.value = await getFeedbacks()
}

const avg = computed(() => {
  if (!feedbacks.value.length) return '—'
  const s = feedbacks.value.reduce((a, f) => a + f.rating, 0)
  return (s / feedbacks.value.length).toFixed(2)
})
const dist = computed(() => {
  const d = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 }
  feedbacks.value.forEach(f => { d[f.rating] = (d[f.rating] || 0) + 1 })
  return d
})

async function openDetail(convId) {
  if (!convId) return
  detail.value = await getConversation(convId)
}
function fmt(ts) {
  return new Date(ts * 1000).toLocaleString('zh-CN', { hour12: false })
}
function stars(n) { return '★'.repeat(n) + '☆'.repeat(5 - n) }
</script>

<template>
  <div class="fb">
    <!-- 汇总 -->
    <div class="summary card">
      <div class="s-item">
        <div class="s-num">{{ avg }}</div>
        <div class="s-label">平均评分</div>
      </div>
      <div class="s-item">
        <div class="s-num">{{ feedbacks.length }}</div>
        <div class="s-label">评价总数</div>
      </div>
      <div class="s-dist">
        <div class="bar-row" v-for="n in [5,4,3,2,1]" :key="n">
          <span class="bl">{{ n }}★</span>
          <div class="bar"><div class="fill" :style="{ width: (feedbacks.length ? (dist[n]/feedbacks.length*100) : 0) + '%' }"></div></div>
          <span class="bc">{{ dist[n] || 0 }}</span>
        </div>
      </div>
    </div>

    <!-- 评价列表 -->
    <div class="card panel">
      <div class="p-title">⭐ 用户评价（{{ feedbacks.length }}）</div>
      <table class="tbl" v-if="feedbacks.length">
        <thead>
          <tr><th>评分</th><th>评价内容</th><th>时间</th><th>关联会话</th></tr>
        </thead>
        <tbody>
          <tr v-for="f in feedbacks" :key="f.id">
            <td class="rating">{{ stars(f.rating) }}</td>
            <td>{{ f.comment || '—' }}</td>
            <td class="weak">{{ fmt(f.created_at) }}</td>
            <td><button class="btn mini" v-if="f.conv_id" @click="openDetail(f.conv_id)">查看</button></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无评价</div>
    </div>

    <!-- 会话详情弹层 -->
    <div class="mask" v-if="detail" @click.self="detail = null">
      <div class="modal card">
        <div class="m-head">
          <span>会话详情</span>
          <button class="btn mini" @click="detail = null">关闭</button>
        </div>
        <div class="m-msgs">
          <div v-for="(m, i) in detail.messages" :key="i" class="dmsg" :class="m.role">
            <div class="role">{{ m.role === 'user' ? '用户' : 'AI' }}</div>
            <div class="text">{{ m.content }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.summary { display: flex; gap: 28px; padding: 18px; margin-bottom: 16px; align-items: center; }
.s-item { text-align: center; }
.s-num { font-size: 26px; font-weight: 700; color: var(--primary); }
.s-label { font-size: 12px; color: var(--text-weak); }
.s-dist { flex: 1; }
.bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.bl { font-size: 12px; color: var(--text-weak); width: 26px; }
.bar { flex: 1; height: 10px; background: #eef1f7; border-radius: 5px; overflow: hidden; }
.fill { height: 100%; background: var(--warn); }
.bc { font-size: 12px; color: var(--text-weak); width: 24px; text-align: right; }

.panel { padding: 16px; }
.p-title { font-weight: 700; font-size: 15px; margin-bottom: 12px; }
.rating { color: var(--warn); white-space: nowrap; }
.weak { color: var(--text-weak); font-size: 12px; }
.btn.mini { padding: 3px 9px; font-size: 12px; }

.mask { position: fixed; inset: 0; background: rgba(20,30,60,.35); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { width: 640px; max-width: 92vw; max-height: 80vh; display: flex; flex-direction: column; padding: 16px; }
.m-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; margin-bottom: 10px; }
.m-msgs { overflow: auto; }
.dmsg { margin-bottom: 10px; }
.dmsg .role { font-size: 11px; color: var(--text-weak); margin-bottom: 2px; }
.dmsg .text { font-size: 13px; line-height: 1.6; white-space: pre-wrap; padding: 8px 10px; border-radius: 8px; }
.dmsg.user .text { background: var(--bubble-user); }
.dmsg.ai .text { background: #f6f8fc; border: 1px solid var(--border); }
</style>

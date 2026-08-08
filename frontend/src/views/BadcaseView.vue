<script setup>
import { ref, onMounted } from 'vue'
import { getBadcases, updateBadcase } from '../api.js'

const statusFilter = ref('')
const badcases = ref([])
const editingReason = ref({})
const msg = ref('')

onMounted(loadAll)
async function loadAll() {
  badcases.value = await getBadcases(statusFilter.value)
}
async function changeStatus(id, status) {
  const reason = editingReason.value[id]
  await updateBadcase(id, status, reason != null ? reason : undefined)
  msg.value = '已更新'
  await loadAll()
}
function fmt(ts) {
  return new Date(ts * 1000).toLocaleString('zh-CN', { hour12: false })
}
const STATUS_LABEL = { pending: '待处理', resolved: '已处理', ignored: '已忽略' }
</script>

<template>
  <div class="bc">
    <div class="toolbar">
      <select v-model="statusFilter" @change="loadAll">
        <option value="">全部状态</option>
        <option value="pending">待处理</option>
        <option value="resolved">已处理</option>
        <option value="ignored">已忽略</option>
      </select>
      <span class="count">共 {{ badcases.length }} 条 Badcase</span>
      <span class="msg">{{ msg }}</span>
    </div>

    <div class="cards">
      <div class="card bc-item" v-for="b in badcases" :key="b.id">
        <div class="bc-head">
          <span class="badge" :class="b.status">{{ STATUS_LABEL[b.status] || b.status }}</span>
          <span class="domain">{{ b.domain }}</span>
          <span class="time">{{ fmt(b.created_at) }}</span>
        </div>
        <div class="qa">
          <div class="lbl">问</div>
          <div class="qt">{{ b.question }}</div>
        </div>
        <div class="qa">
          <div class="lbl a">答</div>
          <div class="at">{{ b.answer }}</div>
        </div>
        <div class="reason">
          <div class="rl">问题原因：</div>
          <textarea v-model="editingReason[b.id]" rows="2" :placeholder="b.reason || '补充分析结论…'"></textarea>
        </div>
        <div class="ops">
          <button class="btn" @click="changeStatus(b.id, 'resolved')">标记已处理</button>
          <button class="btn" @click="changeStatus(b.id, 'ignored')">忽略</button>
          <button class="btn primary" @click="changeStatus(b.id, 'pending')">重置待处理</button>
        </div>
      </div>
    </div>

    <div v-if="!badcases.length" class="empty card" style="padding:40px">暂无 Badcase（用户评分 ≤ 2 星会自动进入此处）</div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.toolbar select { font-size: 13px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border); }
.count { font-size: 13px; color: var(--text-weak); }
.msg { font-size: 13px; color: var(--primary); }

.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 14px; }
.bc-item { padding: 14px; }
.bc-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.domain { font-size: 12px; color: var(--text-weak); }
.time { font-size: 11px; color: var(--text-weak); margin-left: auto; }

.qa { display: flex; gap: 8px; margin-bottom: 8px; }
.lbl { flex-shrink: 0; width: 22px; height: 22px; border-radius: 6px; background: var(--primary-soft); color: var(--primary); font-size: 12px; display: flex; align-items: center; justify-content: center; }
.lbl.a { background: #fdeaea; color: var(--danger); }
.qt { font-size: 13px; font-weight: 600; line-height: 1.5; }
.at { font-size: 13px; line-height: 1.6; color: var(--text); white-space: pre-wrap; }

.reason { margin: 8px 0; }
.rl { font-size: 12px; color: var(--text-weak); margin-bottom: 4px; }
.reason textarea { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 8px; font-size: 13px; font-family: inherit; resize: vertical; }

.ops { display: flex; gap: 8px; flex-wrap: wrap; }
.btn { padding: 5px 12px; font-size: 12px; }
</style>

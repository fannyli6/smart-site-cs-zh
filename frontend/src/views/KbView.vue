<script setup>
import { ref, onMounted } from 'vue'
import {
  getDomains, getStats, uploadDoc, previewChunks, getDocuments, deleteDocument,
} from '../api.js'

const domains = ref([])
const stats = ref({ total_chunks: 0, by_domain: {} })
const documents = ref([])

const uploadFile = ref(null)
const uploadDomain = ref('device_fault')
const uploading = ref(false)
const uploadMsg = ref('')

const previewFile = ref(null)
const previewDomain = ref('device_fault')
const previewing = ref(false)
const previewData = ref(null)
const previewMsg = ref('')

onMounted(loadAll)
async function loadAll() {
  domains.value = await getDomains()
  try { stats.value = await getStats() } catch (e) {}
  await loadDocs()
}
async function loadDocs() {
  documents.value = await getDocuments()
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
    if (r.status === 'ok') { stats.value = await getStats(); await loadDocs() }
  } catch (e) {
    uploadMsg.value = '❌ ' + e.message
  } finally {
    uploading.value = false
  }
}

async function doPreview() {
  if (!previewFile.value) { previewMsg.value = '请先选择文件预览'; return }
  previewing.value = true
  previewData.value = null
  previewMsg.value = '解析与切片中…'
  try {
    const r = await previewChunks(previewFile.value, previewDomain.value)
    if (r.status === 'ok') {
      previewData.value = r
      previewMsg.value = ''
    } else {
      previewMsg.value = '❌ ' + (r.msg || '预览失败')
    }
  } catch (e) {
    previewMsg.value = '❌ ' + e.message
  } finally {
    previewing.value = false
  }
}

async function doDelete(source) {
  if (!confirm(`确认删除《${source}》及其所有切片？`)) return
  const r = await deleteDocument(source)
  if (r.status === 'ok') { stats.value = await getStats(); await loadDocs() }
}
</script>

<template>
  <div class="kb">
    <!-- 概览 -->
    <div class="row-cards">
      <div class="kpi card">
        <div class="k-num">{{ stats.total_chunks }}</div>
        <div class="k-label">知识切片总数</div>
      </div>
      <div class="kpi card" v-for="d in domains" :key="d.key">
        <div class="k-num">{{ stats.by_domain[d.key] || 0 }}</div>
        <div class="k-label">{{ d.label }}</div>
      </div>
    </div>

    <div class="grid">
      <!-- 上传并索引 -->
      <div class="card panel">
        <div class="p-title">📥 上传并索引</div>
        <div class="row">
          <label>领域</label>
          <select v-model="uploadDomain">
            <option v-for="d in domains" :key="d.key" :value="d.key">{{ d.label }}</option>
          </select>
        </div>
        <div class="row">
          <input type="file" @change="e => uploadFile = e.target.files[0]" accept=".pdf,.docx,.xlsx,.md,.txt" />
        </div>
        <div class="row">
          <button class="btn primary" :disabled="uploading" @click="doUpload">
            {{ uploading ? '处理中…' : '开始索引' }}
          </button>
          <span class="msg">{{ uploadMsg }}</span>
        </div>
        <div class="hint">支持 PDF / Word / Excel / Markdown / TXT，自动解析、切片、向量化入库。</div>
      </div>

      <!-- 切片预览 -->
      <div class="card panel">
        <div class="p-title">🔪 切分预览（不入库）</div>
        <div class="row">
          <label>领域</label>
          <select v-model="previewDomain">
            <option v-for="d in domains" :key="d.key" :value="d.key">{{ d.label }}</option>
          </select>
        </div>
        <div class="row">
          <input type="file" @change="e => previewFile = e.target.files[0]" accept=".pdf,.docx,.xlsx,.md,.txt" />
        </div>
        <div class="row">
          <button class="btn" :disabled="previewing" @click="doPreview">
            {{ previewing ? '切片中…' : '预览切片' }}
          </button>
          <span class="msg">{{ previewMsg }}</span>
        </div>
        <div class="hint">只解析并切分，便于调整策略；确认无误后再用左侧「上传并索引」正式入库。</div>

        <div v-if="previewData" class="preview">
          <div class="pv-head">
            共解析 <b>{{ previewData.plain_length }}</b> 字，切成 <b>{{ previewData.chunk_count }}</b> 片
          </div>
          <div v-for="c in previewData.chunks" :key="c.index" class="pv-item">
            <div class="pv-meta">
              <span class="pv-idx">#{{ c.index }}</span>
              <span v-if="c.section" class="tag">{{ c.section }}</span>
              <span class="pv-len">{{ c.length }} 字</span>
            </div>
            <div class="pv-text">{{ c.text }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="card panel">
      <div class="p-title">📄 已上传文档（{{ documents.length }}）</div>
      <table class="tbl" v-if="documents.length">
        <thead>
          <tr><th>文件名</th><th>领域</th><th>切片数</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="d in documents" :key="d.source">
            <td>{{ d.filename }}</td>
            <td>{{ d.domain }}</td>
            <td>{{ d.chunks }}</td>
            <td><button class="btn danger" @click="doDelete(d.source)">删除</button></td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无文档，上传一个试试。</div>
    </div>
  </div>
</template>

<style scoped>
.row-cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.kpi { padding: 14px 18px; min-width: 120px; }
.k-num { font-size: 24px; font-weight: 700; color: var(--primary); }
.k-label { font-size: 12px; color: var(--text-weak); margin-top: 2px; }

.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
@media (max-width: 980px) { .grid { grid-template-columns: 1fr; } }

.panel { padding: 16px; }
.p-title { font-weight: 700; font-size: 15px; margin-bottom: 12px; }
.row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.row label { font-size: 13px; color: var(--text-weak); width: 40px; }
.row select, .row input[type=file] { font-size: 13px; }
.msg { color: var(--primary); font-size: 13px; }
.hint { color: var(--text-weak); font-size: 12px; margin-top: 4px; line-height: 1.5; }

.preview { margin-top: 12px; border-top: 1px dashed var(--border); padding-top: 10px; max-height: 360px; overflow: auto; }
.pv-head { font-size: 13px; margin-bottom: 8px; color: var(--text); }
.pv-item { border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; margin-bottom: 8px; background: #fafbfe; }
.pv-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.pv-idx { font-weight: 700; color: var(--primary); }
.pv-len { font-size: 12px; color: var(--text-weak); }
.pv-text { font-size: 12px; color: var(--text); white-space: pre-wrap; line-height: 1.5; max-height: 120px; overflow: auto; }
</style>

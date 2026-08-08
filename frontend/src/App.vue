<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const menus = [
  { to: '/chat', label: '智能对话', icon: '💬' },
  { to: '/kb', label: '知识库管理', icon: '📚' },
  { to: '/history', label: '历史对话', icon: '🕘' },
  { to: '/feedback', label: '用户评价', icon: '⭐' },
  { to: '/badcase', label: 'Badcase 分析', icon: '🐞' },
]
const activeTitle = computed(() => route.meta.title || '智慧工地 AI 客服')
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">🏗️</span>
        <div class="brand-txt">
          <div class="b1">智慧工地</div>
          <div class="b2">AI 客服控制台</div>
        </div>
      </div>
      <nav class="nav">
        <router-link
          v-for="m in menus"
          :key="m.to"
          :to="m.to"
          class="nav-item"
          :class="{ active: route.path.startsWith(m.to) }"
        >
          <span class="ico">{{ m.icon }}</span>
          <span>{{ m.label }}</span>
        </router-link>
      </nav>
      <div class="side-foot">v1.1 · 私有化部署</div>
    </aside>

    <main class="main">
      <header class="main-head">
        <div class="h-title">{{ activeTitle }}</div>
        <div class="h-sub">基于知识库的专业答疑 · 数据私有 · 流式问答</div>
      </header>
      <section class="content">
        <router-view />
      </section>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.sidebar {
  width: 220px;
  background: var(--sidebar);
  color: #cdd5e6;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
}
.brand .logo { font-size: 26px; }
.brand-txt .b1 { font-weight: 700; color: #fff; font-size: 16px; }
.brand-txt .b2 { font-size: 12px; color: #9aa6c4; }
.nav { padding: 10px 10px; flex: 1; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 8px;
  color: #cdd5e6;
  margin-bottom: 4px;
  font-size: 14px;
  transition: background .15s;
}
.nav-item:hover { background: var(--sidebar-active); color: #fff; }
.nav-item.active { background: var(--primary); color: #fff; }
.nav-item .ico { font-size: 16px; }
.side-foot { padding: 12px 16px; font-size: 11px; color: #6b7798; }

.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.main-head {
  padding: 14px 22px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
}
.main-head .h-title { font-size: 18px; font-weight: 700; }
.main-head .h-sub { font-size: 12px; color: var(--text-weak); margin-top: 3px; }
.content { flex: 1; overflow: auto; padding: 20px 22px; }
</style>

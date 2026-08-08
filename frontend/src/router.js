import { createRouter, createWebHistory } from 'vue-router'
import ChatView from './views/ChatView.vue'
import KbView from './views/KbView.vue'
import HistoryView from './views/HistoryView.vue'
import FeedbackView from './views/FeedbackView.vue'
import BadcaseView from './views/BadcaseView.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', name: 'chat', component: ChatView, meta: { title: '智能对话' } },
  { path: '/kb', name: 'kb', component: KbView, meta: { title: '知识库管理' } },
  { path: '/history', name: 'history', component: HistoryView, meta: { title: '历史对话' } },
  { path: '/feedback', name: 'feedback', component: FeedbackView, meta: { title: '用户评价' } },
  { path: '/badcase', name: 'badcase', component: BadcaseView, meta: { title: 'Badcase 分析' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})

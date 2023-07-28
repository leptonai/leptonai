import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('@/views/AboutView.vue')
  },
  {
    path: '/test',
    name: 'TestView',
    component: () => import('@/views/TestView.vue')
  },
  {
    path: '/workspaces',
    name: 'WorkspacesView',
    component: () => import('@/views/WorkspacesView.vue')
  }

]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router

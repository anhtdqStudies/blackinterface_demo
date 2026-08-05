import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

/**
 * Hash history on purpose: FastAPI serves `dist/index.html` at `/` only, and
 * hash routing means a refresh on a deep link works without a catch-all route
 * on the server. One fewer thing to get wrong in the installer (ADR-0009).
 */
const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/station' },
  {
    path: '/station',
    name: 'station',
    component: () => import('@/views/StationView.vue'),
  },
  {
    path: '/bay/:bayId',
    name: 'bay',
    component: () => import('@/views/BayView.vue'),
    props: true,
  },
  {
    path: '/issues',
    name: 'issues',
    component: () => import('@/views/IssuesView.vue'),
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('@/views/ProjectsView.vue'),
  },
  { path: '/:pathMatch(.*)*', redirect: '/station' },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

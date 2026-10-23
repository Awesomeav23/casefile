import { createRouter, createWebHistory } from 'vue-router'
import { applyTitle, routes } from './routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.afterEach(applyTitle)

export default router

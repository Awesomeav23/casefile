import type { RouteLocationNormalized, RouteRecordRaw } from 'vue-router'
import { m } from '@/i18n'

declare module 'vue-router' {
  interface RouteMeta {
    /** Document title (without the " · Casefile" suffix). */
    title?: string
    /**
     * Guest play (D-01): no route requires an account. Only the account *section* of
     * Settings does, inside the page. Kept here so a test can enforce it.
     */
    requiresAccount?: boolean
  }
}

const s = m.screens

/** Every screen from docs/SCREEN_DESIGN.md §1. Views are lazy-loaded per route. */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/views/LandingView.vue'),
    meta: { title: s.landing.title },
  },
  {
    path: '/login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: s.login.title },
  },
  {
    path: '/register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: s.register.title },
  },
  {
    path: '/reset-password',
    component: () => import('@/views/ResetPasswordView.vue'),
    meta: { title: s.resetPassword.title },
  },
  {
    path: '/cases',
    component: () => import('@/views/LibraryView.vue'),
    meta: { title: s.library.title },
  },
  {
    path: '/cases/:slug',
    component: () => import('@/views/BriefingView.vue'),
    meta: { title: s.briefing.title },
  },
  {
    path: '/play/:playthroughId',
    component: () => import('@/views/workspace/WorkspaceLayout.vue'),
    children: [
      { path: '', redirect: (to) => `/play/${String(to.params.playthroughId)}/overview` },
      {
        path: 'overview',
        component: () => import('@/views/workspace/OverviewView.vue'),
        meta: { title: s.overview.title },
      },
      {
        path: 'locations/:key?',
        component: () => import('@/views/workspace/LocationsView.vue'),
        meta: { title: s.locations.title },
      },
      {
        path: 'evidence/:key?',
        component: () => import('@/views/workspace/EvidenceView.vue'),
        meta: { title: s.evidence.title },
      },
      {
        path: 'people/:key?',
        component: () => import('@/views/workspace/PeopleView.vue'),
        meta: { title: s.people.title },
      },
      {
        path: 'timeline',
        component: () => import('@/views/workspace/TimelineView.vue'),
        meta: { title: s.timeline.title },
      },
      {
        path: 'board',
        component: () => import('@/views/workspace/BoardView.vue'),
        meta: { title: s.board.title },
      },
      {
        path: 'theories/:theoryId?',
        component: () => import('@/views/workspace/TheoriesView.vue'),
        meta: { title: s.theories.title },
      },
    ],
  },
  {
    path: '/play/:playthroughId/accuse',
    component: () => import('@/views/AccuseView.vue'),
    meta: { title: s.accuse.title },
  },
  {
    path: '/play/:playthroughId/results',
    component: () => import('@/views/ResultsView.vue'),
    meta: { title: s.results.title },
  },
  {
    path: '/progress',
    component: () => import('@/views/ProgressView.vue'),
    meta: { title: s.progress.title },
  },
  {
    path: '/settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: s.settings.title },
  },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: s.notFound.title },
  },
]

export function applyTitle(to: RouteLocationNormalized) {
  const title = to.meta.title
  document.title = !title || title === m.app.name ? m.app.name : `${title} · ${m.app.name}`
}

import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '@/App.vue'
import { applyTitle, routes } from '@/router/routes'
import { axeViolations, describeViolations } from '@/test/a11y'

async function renderAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.afterEach(applyTitle)
  router.push(path)
  await router.isReady()
  const wrapper = mount(App, {
    global: { plugins: [router, createPinia()] },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, router }
}

// Every screen in docs/SCREEN_DESIGN.md §1, with the heading its placeholder must show.
const screens: [string, string][] = [
  ['/', 'Casefile'],
  ['/login', 'Log in'],
  ['/register', 'Create an account'],
  ['/reset-password', 'Reset your password'],
  ['/cases', 'Case library'],
  ['/cases/the-missing-masterpiece', 'Case briefing'],
  ['/play/p1/overview', 'Overview'],
  ['/play/p1/locations', 'Locations'],
  ['/play/p1/locations/east-room', 'Locations'],
  ['/play/p1/evidence', 'Evidence'],
  ['/play/p1/evidence/alarm-log', 'Evidence'],
  ['/play/p1/people', 'People'],
  ['/play/p1/people/corinne-blake', 'People'],
  ['/play/p1/timeline', 'Timeline'],
  ['/play/p1/board', 'Evidence board'],
  ['/play/p1/theories', 'Theories'],
  ['/play/p1/theories/t1', 'Theories'],
  ['/play/p1/accuse', 'Final accusation'],
  ['/play/p1/results', 'Case results'],
  ['/progress', 'Your progress'],
  ['/settings', 'Settings'],
]

describe('routes', () => {
  it.each(screens)('%s renders the "%s" placeholder', async (path, heading) => {
    const { wrapper } = await renderAt(path)
    expect(wrapper.find('main h1').text()).toBe(heading)
    expect(document.title).toBe(heading === 'Casefile' ? 'Casefile' : `${heading} · Casefile`)
  })

  it('redirects /play/:id to the overview', async () => {
    const { router } = await renderAt('/play/p1')
    expect(router.currentRoute.value.fullPath).toBe('/play/p1/overview')
  })

  it('shows the 404 screen for unknown routes', async () => {
    const { wrapper } = await renderAt('/no/such/page')
    expect(wrapper.find('main h1').text()).toBe('File not found')
    expect(wrapper.find('main a[href="/cases"]').exists()).toBe(true)
  })

  it('requires an account for no route (guest play, D-01)', () => {
    const all = routes.flatMap((r) => [r, ...(r.children ?? [])])
    expect(all.every((r) => r.meta?.requiresAccount !== true)).toBe(true)
  })

  it('has a skip link to the main landmark', async () => {
    const { wrapper } = await renderAt('/cases')
    expect(wrapper.find('a.skip-link').attributes('href')).toBe('#main')
    expect(wrapper.find('main#main').exists()).toBe(true)
  })

  it.each(['/', '/cases', '/play/p1/overview', '/no/such/page'])(
    'the app shell at %s has no axe violations',
    async (path) => {
      const { wrapper } = await renderAt(path)
      const v = await axeViolations(wrapper.element)
      expect(v, describeViolations(v)).toEqual([])
    },
  )
})

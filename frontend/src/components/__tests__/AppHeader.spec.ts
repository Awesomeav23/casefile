import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import * as authApi from '@/api/endpoints/auth'
import { routes } from '@/router/routes'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/endpoints/auth')

async function render() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push('/cases')
  await router.isReady()
  return { wrapper: mount(AppHeader, { global: { plugins: [router] } }), router }
}

describe('AppHeader', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('offers log in to visitors and guests', async () => {
    const { wrapper } = await render()
    expect(wrapper.find('a[href="/login"]').text()).toBe('Log in')
  })

  it('shows the account name and logs out', async () => {
    vi.mocked(authApi.logout).mockResolvedValue(undefined)
    const auth = useAuthStore()
    auth.user = {
      id: 1,
      email: 'sam@example.com',
      display_name: 'Sam',
      is_staff: false,
      preferences: { text_scale: 1, reduced_motion: false, theme: 'dark', show_tips: true },
    }
    const { wrapper, router } = await render()
    expect(wrapper.text()).toContain('Sam')
    expect(wrapper.find('a[href="/login"]').exists()).toBe(false)
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Log out')!
      .trigger('click')
    await flushPromises()
    expect(auth.kind).toBe('visitor')
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/'))
  })
})

import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import ResetPasswordView from '@/views/ResetPasswordView.vue'
import { routes } from '@/router/routes'
import * as authApi from '@/api/endpoints/auth'
import { ApiError } from '@/api/client'
import { axeViolations, describeViolations } from '@/test/a11y'

vi.mock('@/api/endpoints/auth')

const user = {
  id: 1,
  email: 'sam@example.com',
  display_name: 'Sam',
  is_staff: false,
  preferences: { text_scale: 1, reduced_motion: false, theme: 'dark', show_tips: true },
}
const noClaim = { playthroughs: [], conflicts: [] }

async function render(component: object, path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(path)
  await router.isReady()
  const wrapper = mount(component, { global: { plugins: [router] }, attachTo: document.body })
  return { wrapper, router }
}

async function fill(wrapper: ReturnType<typeof mount>, label: string, value: string) {
  const id = wrapper
    .findAll('label')
    .find((l) => l.text() === label)!
    .attributes('for')
  const input = wrapper.find(`#${id}`)
  await input.setValue(value)
  await input.trigger('blur')
}

describe('login view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('explains the benefit of an account and links to register', async () => {
    const { wrapper } = await render(LoginView, '/login')
    expect(wrapper.text()).toContain('Keep your progress across devices')
    expect(wrapper.find('a[href="/register"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/reset-password"]').exists()).toBe(true)
  })

  it('validates on blur before submitting', async () => {
    const { wrapper } = await render(LoginView, '/login')
    await fill(wrapper, 'Email', 'not-an-email')
    expect(wrapper.text()).toContain('Enter a valid email address.')
    await wrapper.find('form').trigger('submit')
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('logs in and goes to a safe `next` path', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ user, claimed: noClaim })
    const { wrapper, router } = await render(LoginView, '/login?next=/progress')
    await fill(wrapper, 'Email', 'sam@example.com')
    await fill(wrapper, 'Password', 'a-long-password-1')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(authApi.login).toHaveBeenCalledWith({
      email: 'sam@example.com',
      password: 'a-long-password-1',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/progress'))
  })

  it('ignores an external `next` and falls back to the library', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ user, claimed: noClaim })
    const { wrapper, router } = await render(LoginView, '/login?next=//evil.example')
    await fill(wrapper, 'Email', 'sam@example.com')
    await fill(wrapper, 'Password', 'pw')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/cases'))
  })

  it('shows the server message for wrong credentials', async () => {
    vi.mocked(authApi.login).mockRejectedValue(
      new ApiError(400, 'invalid_credentials', "That email and password don't match."),
    )
    const { wrapper } = await render(LoginView, '/login')
    await fill(wrapper, 'Email', 'sam@example.com')
    await fill(wrapper, 'Password', 'wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toBe("That email and password don't match.")
  })

  it('has no axe violations', async () => {
    const { wrapper } = await render(LoginView, '/login')
    const v = await axeViolations(wrapper.element)
    expect(v, describeViolations(v)).toEqual([])
  })
})

describe('register view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('maps server field errors onto the fields', async () => {
    vi.mocked(authApi.register).mockRejectedValue(
      new ApiError(400, 'validation_error', 'Some fields are invalid.', {
        email: ['An account with this email already exists.'],
      }),
    )
    const { wrapper } = await render(RegisterView, '/register')
    await fill(wrapper, 'Display name', 'Sam')
    await fill(wrapper, 'Email', 'sam@example.com')
    await fill(wrapper, 'Password', 'a-long-password-1')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('An account with this email already exists.')
  })

  it('checks password length on blur', async () => {
    const { wrapper } = await render(RegisterView, '/register')
    await fill(wrapper, 'Password', 'short')
    expect(wrapper.text()).toContain('Use at least 8 characters.')
  })

  it('registers and goes to the library', async () => {
    vi.mocked(authApi.register).mockResolvedValue({ user, claimed: noClaim })
    const { wrapper, router } = await render(RegisterView, '/register')
    await fill(wrapper, 'Display name', 'Sam')
    await fill(wrapper, 'Email', 'sam@example.com')
    await fill(wrapper, 'Password', 'a-long-password-1')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/cases'))
  })

  it('has no axe violations', async () => {
    const { wrapper } = await render(RegisterView, '/register')
    const v = await axeViolations(wrapper.element)
    expect(v, describeViolations(v)).toEqual([])
  })
})

describe('reset password view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('requests a reset and shows the same confirmation for any email', async () => {
    vi.mocked(authApi.requestPasswordReset).mockResolvedValue({ detail: 'If an account exists…' })
    const { wrapper } = await render(ResetPasswordView, '/reset-password')
    await fill(wrapper, 'Email', 'anyone@example.com')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="status"]').text()).toContain('Check your email')
  })

  it('sets a new password from the emailed link', async () => {
    vi.mocked(authApi.confirmPasswordReset).mockResolvedValue(undefined)
    const { wrapper } = await render(ResetPasswordView, '/reset-password?uid=MQ&token=abc')
    await fill(wrapper, 'New password', 'brand-new-pass-3')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(authApi.confirmPasswordReset).toHaveBeenCalledWith({
      uid: 'MQ',
      token: 'abc',
      new_password: 'brand-new-pass-3',
    })
    expect(wrapper.find('[role="status"]').text()).toContain('Your password has been changed')
    expect(wrapper.find('a[href="/login"]').exists()).toBe(true)
  })

  it('has no axe violations in either mode', async () => {
    for (const path of ['/reset-password', '/reset-password?uid=MQ&token=abc']) {
      const { wrapper } = await render(ResetPasswordView, path)
      const v = await axeViolations(wrapper.element)
      expect(v, describeViolations(v)).toEqual([])
    }
  })
})

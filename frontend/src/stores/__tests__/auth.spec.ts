import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'
import * as authApi from '@/api/endpoints/auth'
import * as client from '@/api/client'

vi.mock('@/api/endpoints/auth')
vi.mock('@/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/client')>()),
  ensureCsrfCookie: vi.fn<() => Promise<void>>(),
}))

const user = {
  id: 1,
  email: 'sam@example.com',
  display_name: 'Sam',
  is_staff: false,
  preferences: { text_scale: 1, reduced_motion: false, theme: 'dark', show_tips: true },
}
const noClaim = { playthroughs: [], conflicts: [] }

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('starts as a visitor and loads the current identity with a CSRF cookie first', async () => {
    vi.mocked(authApi.getMe).mockResolvedValue({
      user: null,
      guest: { has_progress: false, expires_after_days: 90 },
    })
    const auth = useAuthStore()
    expect(auth.kind).toBe('visitor')
    await auth.load()
    expect(client.ensureCsrfCookie).toHaveBeenCalledOnce()
    expect(auth.loaded).toBe(true)
    expect(auth.kind).toBe('guest')
  })

  it('logs in, keeps the claim result, and logs out', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ user, claimed: noClaim })
    vi.mocked(authApi.logout).mockResolvedValue(undefined)
    const auth = useAuthStore()
    await auth.login({ email: 'sam@example.com', password: 'pw' })
    expect(auth.kind).toBe('account')
    expect(auth.user?.display_name).toBe('Sam')
    expect(auth.lastClaim).toEqual(noClaim)
    await auth.logout()
    expect(auth.kind).toBe('visitor')
  })

  it('registers', async () => {
    vi.mocked(authApi.register).mockResolvedValue({ user, claimed: noClaim })
    const auth = useAuthStore()
    await auth.register({ email: 'sam@example.com', password: 'pw', display_name: 'Sam' })
    expect(auth.kind).toBe('account')
  })

  it('forgets the user when the API says the session has gone', () => {
    const auth = useAuthStore()
    auth.user = user
    auth.sessionExpired()
    expect(auth.kind).toBe('visitor')
  })
})

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ensureCsrfCookie } from '@/api/client'
import * as authApi from '@/api/endpoints/auth'
import type { Claimed, Guest, User } from '@/api/endpoints/auth'

/** Who the visitor is (D-01): an account holder, a guest with saved progress, or a visitor. */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const guest = ref<Guest | null>(null)
  const loaded = ref(false)
  /** Guest progress moved into the account at the last login/register (filled from M7). */
  const lastClaim = ref<Claimed | null>(null)

  const kind = computed<'account' | 'guest' | 'visitor'>(() =>
    user.value ? 'account' : guest.value ? 'guest' : 'visitor',
  )

  async function load() {
    await ensureCsrfCookie()
    const me = await authApi.getMe()
    user.value = me.user
    guest.value = me.guest
    loaded.value = true
  }

  function signedIn(result: authApi.AuthResult) {
    user.value = result.user
    guest.value = null
    lastClaim.value = result.claimed
  }

  async function login(body: { email: string; password: string }) {
    signedIn(await authApi.login(body))
  }

  async function register(body: { email: string; password: string; display_name: string }) {
    signedIn(await authApi.register(body))
  }

  async function logout() {
    await authApi.logout()
    user.value = null
    guest.value = null
    lastClaim.value = null
  }

  /** Called by the API client on a 401 from an account-only endpoint. */
  function sessionExpired() {
    user.value = null
  }

  return { user, guest, loaded, lastClaim, kind, load, login, register, logout, sessionExpired }
})

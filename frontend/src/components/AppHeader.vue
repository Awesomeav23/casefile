<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import UiButton from '@/components/ui/UiButton.vue'
import { m } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'

const auth = useAuthStore()
const router = useRouter()
const busy = ref(false)

async function logOut() {
  busy.value = true
  try {
    await auth.logout()
    await router.push('/')
  } catch {
    useToastStore().push({ message: m.errors.unexpected, tone: 'error' })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <header class="app-header">
    <RouterLink to="/" class="app-header__brand">{{ m.app.name }}</RouterLink>
    <nav :aria-label="m.nav.main">
      <ul class="app-header__nav">
        <li>
          <RouterLink to="/cases">{{ m.nav.cases }}</RouterLink>
        </li>
        <li>
          <RouterLink to="/progress">{{ m.nav.progress }}</RouterLink>
        </li>
        <li>
          <RouterLink to="/settings">{{ m.nav.settings }}</RouterLink>
        </li>
        <li v-if="auth.user" class="app-header__account">
          <span class="app-header__name" :title="m.auth.signedInAs(auth.user.display_name)">
            {{ auth.user.display_name }}
          </span>
          <UiButton variant="ghost" size="sm" :busy="busy" @click="logOut">{{
            m.auth.logOut
          }}</UiButton>
        </li>
        <li v-else>
          <RouterLink to="/login">{{ m.nav.logIn }}</RouterLink>
        </li>
      </ul>
    </nav>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.app-header__brand {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-text);
  text-decoration: none;
}
.app-header__nav {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-4);
  list-style: none;
  margin: 0;
  padding: 0;
}
.app-header__nav a {
  color: var(--color-text);
  text-decoration: none;
}
.app-header__nav a.router-link-active {
  color: var(--color-accent);
}
.app-header__account {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.app-header__name {
  color: var(--color-text-muted);
}
</style>

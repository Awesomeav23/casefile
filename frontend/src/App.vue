<script setup lang="ts">
import UiToastRegion from '@/components/ui/UiToastRegion.vue'
import { m } from '@/i18n'
</script>

<template>
  <a class="skip-link" href="#main">{{ m.app.skipToContent }}</a>
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
        <li>
          <RouterLink to="/login">{{ m.nav.logIn }}</RouterLink>
        </li>
      </ul>
    </nav>
  </header>
  <main id="main" tabindex="-1" class="app-main">
    <RouterView />
  </main>
  <UiToastRegion />
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
.app-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-5) var(--space-7);
}
.app-main:focus {
  outline: none;
}
</style>

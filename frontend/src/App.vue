<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
import UiToastRegion from '@/components/ui/UiToastRegion.vue'
import { m } from '@/i18n'
</script>

<template>
  <a class="skip-link" href="#main">{{ m.app.skipToContent }}</a>
  <AppHeader />
  <main id="main" tabindex="-1" class="app-main">
    <RouterView />
  </main>
  <UiToastRegion />
</template>

<style scoped>
.app-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-5) var(--space-7);
}
.app-main:focus {
  outline: none;
}
</style>

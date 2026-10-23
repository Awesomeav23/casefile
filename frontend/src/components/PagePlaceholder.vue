<script setup lang="ts">
/** Temporary screen body until the screen's milestone builds it (roadmap M2). */
import { m } from '@/i18n'

defineProps<{ title: string; milestone: string }>()
</script>

<template>
  <section class="page-placeholder">
    <h1>{{ title }}</h1>
    <p class="page-placeholder__note">{{ m.common.plannedIn(milestone) }}</p>
    <slot />
  </section>
</template>

<style scoped>
.page-placeholder {
  padding: var(--space-6) 0;
}
.page-placeholder__note {
  color: var(--color-text-muted);
}
</style>

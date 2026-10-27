<script setup lang="ts">
/** Centred card for the auth screens (SCREEN_DESIGN §4). */
defineProps<{ title: string; lead?: string }>()
</script>

<template>
  <section class="auth-card">
    <h1 class="auth-card__title">{{ title }}</h1>
    <p v-if="lead" class="auth-card__lead">{{ lead }}</p>
    <slot />
  </section>
</template>

<style scoped>
.auth-card {
  width: min(28rem, 100%);
  margin: var(--space-7) auto;
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-2);
}
.auth-card__title {
  font-size: var(--text-2xl);
}
.auth-card__lead {
  color: var(--color-text-muted);
}
.auth-card :deep(form) {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-5);
}
.auth-card :deep(.auth-card__links) {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-5);
  font-size: var(--text-sm);
}
.auth-card :deep(.auth-card__alert) {
  margin: 0;
  padding: var(--space-3);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
}
.auth-card :deep(.auth-card__status) {
  margin: var(--space-4) 0 0;
  padding: var(--space-3);
  border: 1px solid var(--verified-500);
  border-radius: var(--radius-sm);
}
</style>

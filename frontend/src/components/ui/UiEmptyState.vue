<script setup lang="ts">
/** Empty state: one-line guidance plus a primary action (SCREEN_DESIGN §2). */
withDefaults(defineProps<{ title: string; body?: string; headingLevel?: 2 | 3 | 4 }>(), {
  body: undefined,
  headingLevel: 2,
})
</script>

<template>
  <div class="ui-empty-state">
    <div class="ui-empty-state__art" aria-hidden="true"><slot name="art">🗂</slot></div>
    <component :is="`h${headingLevel}`" class="ui-empty-state__title">{{ title }}</component>
    <p v-if="body" class="ui-empty-state__body">{{ body }}</p>
    <div v-if="$slots.action" class="ui-empty-state__action"><slot name="action" /></div>
  </div>
</template>

<style scoped>
.ui-empty-state {
  display: grid;
  justify-items: center;
  gap: var(--space-2);
  padding: var(--space-7) var(--space-5);
  text-align: center;
}
.ui-empty-state__art {
  font-size: var(--text-3xl);
}
.ui-empty-state__title {
  font-family: var(--font-ui);
  font-size: var(--text-xl);
  margin: 0;
}
.ui-empty-state__body {
  max-width: 45ch;
  color: var(--color-text-muted);
  margin: 0;
}
.ui-empty-state__action {
  margin-top: var(--space-3);
}
</style>

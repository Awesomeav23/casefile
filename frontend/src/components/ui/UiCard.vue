<script setup lang="ts">
/** Card on ink (chrome) or paper (readable content), per UI_UX_GUIDELINES §1. */
withDefaults(defineProps<{ surface?: 'ink' | 'paper'; as?: string }>(), {
  surface: 'ink',
  as: 'div',
})
</script>

<template>
  <component :is="as" class="ui-card" :class="`ui-card--${surface}`">
    <slot />
  </component>
</template>

<style scoped>
.ui-card {
  padding: var(--space-5);
}
.ui-card--ink {
  background: var(--color-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-1);
}
.ui-card--paper {
  background: var(--paper-100);
  color: var(--paper-ink);
  border-radius: var(--radius-paper);
  box-shadow: var(--shadow-paper);
  font-family: var(--font-document);
  font-size: var(--text-lg);
  line-height: var(--leading-relaxed);
}
.ui-card--paper :deep(:focus-visible) {
  outline-color: var(--brass-600);
}
</style>

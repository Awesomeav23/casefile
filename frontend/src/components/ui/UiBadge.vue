<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'neutral' | 'accent' | 'danger' | 'verified' | 'new' }>(), {
  tone: 'neutral',
})
</script>

<template>
  <span class="ui-badge" :class="`ui-badge--${tone}`"><slot /></span>
</template>

<style scoped>
.ui-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  line-height: 1.6;
  letter-spacing: 0.02em;
  color: var(--color-text);
  white-space: nowrap;
}
.ui-badge--accent,
.ui-badge--new {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-on-accent);
}
/* Red and green mark the boundary only; text stays light for 4.5:1 (tokens.css). */
.ui-badge--danger {
  border-color: var(--color-danger);
}
.ui-badge--verified {
  border-color: var(--verified-500);
}
</style>

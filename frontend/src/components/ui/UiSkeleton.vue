<script setup lang="ts">
/** Loading placeholder shaped like the content (SCREEN_DESIGN §2). Hidden from screen readers. */
withDefaults(
  defineProps<{ shape?: 'text' | 'block' | 'circle'; lines?: number; height?: string }>(),
  { shape: 'text', lines: 1, height: undefined },
)
</script>

<template>
  <div class="ui-skeleton" :class="`ui-skeleton--${shape}`" aria-hidden="true">
    <template v-if="shape === 'text'">
      <span v-for="n in lines" :key="n" class="ui-skeleton__line" />
    </template>
    <span v-else class="ui-skeleton__shape" :style="height ? { height } : undefined" />
  </div>
</template>

<style scoped>
.ui-skeleton {
  display: grid;
  gap: var(--space-2);
}
.ui-skeleton__line,
.ui-skeleton__shape {
  display: block;
  background: linear-gradient(90deg, var(--ink-700), var(--ink-600), var(--ink-700));
  background-size: 200% 100%;
  border-radius: var(--radius-sm);
  animation: ui-shimmer 1.4s ease-in-out infinite;
}
.ui-skeleton__line {
  height: 0.9em;
}
.ui-skeleton__line:last-child:not(:first-child) {
  width: 60%;
}
.ui-skeleton--block .ui-skeleton__shape {
  height: 8rem;
}
.ui-skeleton--circle .ui-skeleton__shape {
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
}
@keyframes ui-shimmer {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: -100% 0;
  }
}
</style>

<script setup lang="ts">
/** Primary/secondary/ghost/danger button (UI_UX_GUIDELINES §6). Busy keeps focus and width. */
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    type?: 'button' | 'submit' | 'reset'
    busy?: boolean
    disabled?: boolean
  }>(),
  { variant: 'secondary', size: 'md', type: 'button', busy: false, disabled: false },
)

const emit = defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <button
    :type="type"
    class="ui-button"
    :class="[`ui-button--${variant}`, `ui-button--${size}`, { 'is-busy': busy }]"
    :disabled="disabled || undefined"
    :aria-busy="busy ? 'true' : undefined"
    :aria-disabled="busy ? 'true' : undefined"
    @click="(e: MouseEvent) => (busy || disabled ? e.preventDefault() : emit('click', e))"
  >
    <span class="ui-button__label"><slot /></span>
    <span v-if="busy" class="ui-button__spinner" aria-hidden="true" />
  </button>
</template>

<style scoped>
.ui-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: var(--pointer-target);
  padding: 0 var(--space-4);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: var(--text-sm);
  cursor: pointer;
  transition:
    background-color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}
@media (pointer: coarse) {
  .ui-button {
    min-height: var(--touch-target);
  }
}
.ui-button--sm {
  padding: 0 var(--space-3);
  font-size: var(--text-xs);
}
.ui-button--lg {
  min-height: var(--touch-target);
  padding: 0 var(--space-5);
  font-size: var(--text-md);
}
.ui-button--primary {
  background: var(--color-accent);
  color: var(--color-on-accent);
}
.ui-button--primary:hover:not(:disabled) {
  background: color-mix(in srgb, var(--brass-400) 85%, white);
}
.ui-button--secondary {
  background: transparent;
  border-color: var(--color-border-strong);
  color: var(--color-text);
}
.ui-button--secondary:hover:not(:disabled) {
  background: var(--color-raised);
}
.ui-button--ghost {
  background: transparent;
  color: var(--color-text);
}
.ui-button--ghost:hover:not(:disabled) {
  background: var(--color-raised);
}
/* Danger is an outline: light text on dark keeps 4.5:1; red marks the boundary (tokens.css). */
.ui-button--danger {
  background: transparent;
  border-color: var(--color-danger);
  color: var(--color-text);
}
.ui-button--danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--tag-red-500) 18%, transparent);
}
.ui-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.is-busy {
  cursor: progress;
}
.is-busy .ui-button__label {
  visibility: hidden; /* keeps the button's width while the spinner shows */
}
.ui-button__spinner {
  position: absolute;
  width: 1em;
  height: 1em;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: ui-spin 0.8s linear infinite;
}
@keyframes ui-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

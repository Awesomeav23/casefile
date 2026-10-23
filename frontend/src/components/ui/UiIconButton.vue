<script setup lang="ts">
/** Icon-only button. `label` is required: it is the accessible name (UI_UX_GUIDELINES §6). */
withDefaults(defineProps<{ label: string; type?: 'button' | 'submit'; disabled?: boolean }>(), {
  type: 'button',
  disabled: false,
})
const emit = defineEmits<{ click: [event: MouseEvent] }>()
</script>

<template>
  <button
    :type="type"
    class="ui-icon-button"
    :aria-label="label"
    :title="label"
    :disabled="disabled || undefined"
    @click="emit('click', $event)"
  >
    <span class="ui-icon-button__icon" aria-hidden="true"><slot /></span>
  </button>
</template>

<style scoped>
.ui-icon-button {
  display: inline-grid;
  place-items: center;
  width: var(--pointer-target);
  height: var(--pointer-target);
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  font-size: var(--text-lg);
}
@media (pointer: coarse) {
  .ui-icon-button {
    width: var(--touch-target);
    height: var(--touch-target);
  }
}
.ui-icon-button:hover:not(:disabled) {
  background: var(--color-raised);
}
.ui-icon-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

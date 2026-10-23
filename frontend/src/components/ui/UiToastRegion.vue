<script setup lang="ts">
/** Stacked toasts in a polite live region, so discoveries are announced (SCREEN_DESIGN §7.1). */
import UiIconButton from './UiIconButton.vue'
import { m } from '@/i18n'
import { useToastStore } from '@/stores/toasts'

const store = useToastStore()

function runAction(id: number, onClick: () => void) {
  onClick()
  store.dismiss(id)
}
</script>

<template>
  <section class="ui-toast-region" :aria-label="m.notifications">
    <div role="status" aria-live="polite" class="ui-toast-region__list">
      <div
        v-for="toast in store.toasts"
        :key="toast.id"
        class="ui-toast"
        :class="`ui-toast--${toast.tone}`"
        @mouseenter="store.pause(toast.id)"
        @mouseleave="store.resume(toast.id)"
        @focusin="store.pause(toast.id)"
        @focusout="store.resume(toast.id)"
      >
        <p class="ui-toast__message">{{ toast.message }}</p>
        <button
          v-if="toast.action"
          type="button"
          class="ui-toast__action"
          @click="runAction(toast.id, toast.action.onClick)"
        >
          {{ toast.action.label }}
        </button>
        <UiIconButton :label="m.common.dismiss" @click="store.dismiss(toast.id)">✕</UiIconButton>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ui-toast-region {
  position: fixed;
  right: var(--space-4);
  bottom: var(--space-4);
  z-index: 900;
  width: min(24rem, calc(100vw - 2 * var(--space-4)));
  pointer-events: none;
}
.ui-toast-region__list {
  display: grid;
  gap: var(--space-2);
}
.ui-toast {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3) var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-raised);
  box-shadow: var(--shadow-2);
  pointer-events: auto;
}
.ui-toast--discovery {
  border-left-color: var(--color-accent);
}
.ui-toast--success {
  border-left-color: var(--verified-500);
}
.ui-toast--error {
  border-left-color: var(--color-danger);
}
.ui-toast__message {
  flex: 1;
  margin: 0;
  font-size: var(--text-sm);
}
.ui-toast__action {
  border: 0;
  background: none;
  color: var(--color-accent);
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
}
</style>

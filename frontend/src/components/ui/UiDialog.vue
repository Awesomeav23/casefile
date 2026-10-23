<script setup lang="ts">
/**
 * Modal dialog or sheet on the native <dialog> element: it supplies the focus trap, Escape to
 * cancel, inert background, and focus return. Open state is controlled with v-model:open.
 */
import { onMounted, ref, useId, watch } from 'vue'
import UiIconButton from './UiIconButton.vue'
import { m } from '@/i18n'

const props = withDefaults(
  defineProps<{ open: boolean; title: string; variant?: 'dialog' | 'sheet' }>(),
  { variant: 'dialog' },
)
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const dialog = ref<HTMLDialogElement | null>(null)
const titleId = `dialog-title-${useId()}`

function sync(open: boolean) {
  const el = dialog.value
  if (!el) return
  if (open && !el.open) el.showModal()
  if (!open && el.open) el.close()
}

onMounted(() => sync(props.open))
watch(() => props.open, sync)

function requestClose() {
  emit('update:open', false)
}

function onCancel(event: Event) {
  event.preventDefault() // the parent owns the state; it closes us via the prop
  requestClose()
}
</script>

<template>
  <dialog
    ref="dialog"
    class="ui-dialog"
    :class="`ui-dialog--${variant}`"
    :aria-labelledby="titleId"
    @cancel="onCancel"
  >
    <header class="ui-dialog__header">
      <h2 :id="titleId" class="ui-dialog__title">{{ title }}</h2>
      <UiIconButton :label="m.common.close" @click="requestClose">✕</UiIconButton>
    </header>
    <div class="ui-dialog__body"><slot /></div>
    <footer v-if="$slots.footer" class="ui-dialog__footer"><slot name="footer" /></footer>
  </dialog>
</template>

<style scoped>
.ui-dialog {
  width: min(36rem, calc(100vw - 2 * var(--space-4)));
  max-height: calc(100vh - 2 * var(--space-6));
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-3);
}
.ui-dialog::backdrop {
  background: rgb(0 0 0 / 0.6);
}
.ui-dialog--sheet {
  margin: 0 0 0 auto;
  width: min(var(--drawer-width), 100vw);
  height: 100vh;
  max-height: 100vh;
  border-radius: 0;
}
@media (max-width: 767px) {
  .ui-dialog,
  .ui-dialog--sheet {
    margin: auto 0 0;
    width: 100vw;
    max-width: 100vw;
    height: auto;
    max-height: 90vh;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }
}
.ui-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}
.ui-dialog__title {
  margin: 0;
  font-family: var(--font-ui);
  font-size: var(--text-lg);
}
.ui-dialog__body {
  padding: var(--space-5);
  overflow: auto;
}
.ui-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-border);
}
</style>

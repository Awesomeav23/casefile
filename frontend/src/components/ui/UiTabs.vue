<script setup lang="ts" generic="T extends string">
/** ARIA tabs with roving tabindex and automatic activation (Arrow keys, Home, End). */
import { nextTick, ref, useId } from 'vue'

const props = defineProps<{ tabs: { id: T; label: string }[]; modelValue: T; label: string }>()
const emit = defineEmits<{ 'update:modelValue': [id: T] }>()
defineSlots<{ default(props: { selected: T }): unknown }>()

const base = `tabs-${useId()}`
const tabEls = ref<HTMLButtonElement[]>([])

function select(index: number) {
  const tab = props.tabs[index]
  if (!tab) return
  emit('update:modelValue', tab.id)
  nextTick(() => tabEls.value[index]?.focus())
}

function onKeydown(event: KeyboardEvent, index: number) {
  const last = props.tabs.length - 1
  const next: Record<string, number> = {
    ArrowRight: index === last ? 0 : index + 1,
    ArrowLeft: index === 0 ? last : index - 1,
    Home: 0,
    End: last,
  }
  const target = next[event.key]
  if (target === undefined) return
  event.preventDefault()
  select(target)
}
</script>

<template>
  <div class="ui-tabs">
    <div role="tablist" :aria-label="label" class="ui-tabs__list">
      <button
        v-for="(tab, index) in tabs"
        :id="`${base}-tab-${tab.id}`"
        :key="tab.id"
        ref="tabEls"
        type="button"
        role="tab"
        class="ui-tabs__tab"
        :aria-selected="tab.id === modelValue ? 'true' : 'false'"
        :aria-controls="`${base}-panel`"
        :tabindex="tab.id === modelValue ? 0 : -1"
        @click="select(index)"
        @keydown="onKeydown($event, index)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div
      :id="`${base}-panel`"
      role="tabpanel"
      class="ui-tabs__panel"
      tabindex="0"
      :aria-labelledby="`${base}-tab-${modelValue}`"
    >
      <slot :selected="modelValue" />
    </div>
  </div>
</template>

<style scoped>
.ui-tabs__list {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--color-border);
  overflow-x: auto;
}
.ui-tabs__tab {
  padding: var(--space-2) var(--space-4);
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--color-text-muted);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.ui-tabs__tab[aria-selected='true'] {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}
.ui-tabs__panel {
  padding-top: var(--space-4);
}
</style>

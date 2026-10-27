<script setup lang="ts">
/** Labelled text input with hint, error, and an optional show/hide toggle for passwords. */
import { computed, ref, useId } from 'vue'
import { m } from '@/i18n'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: string
    type?: 'text' | 'email' | 'password'
    error?: string | null
    hint?: string
    autocomplete?: string
    required?: boolean
    name?: string
  }>(),
  {
    type: 'text',
    error: null,
    hint: undefined,
    autocomplete: undefined,
    required: false,
    name: undefined,
  },
)
const emit = defineEmits<{ 'update:modelValue': [value: string]; blur: [] }>()

const id = `field-${useId()}`
const revealed = ref(false)
const inputType = computed(() =>
  props.type === 'password' && revealed.value ? 'text' : props.type,
)
const describedBy = computed(
  () =>
    [props.hint && `${id}-hint`, props.error && `${id}-error`].filter(Boolean).join(' ') ||
    undefined,
)
</script>

<template>
  <div class="ui-field" :class="{ 'has-error': error }">
    <label :for="id" class="ui-field__label">{{ label }}</label>
    <div class="ui-field__control">
      <input
        :id="id"
        class="ui-field__input"
        :type="inputType"
        :name="name"
        :value="modelValue"
        :autocomplete="autocomplete"
        :required="required || undefined"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="describedBy"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @blur="emit('blur')"
      />
      <button
        v-if="type === 'password'"
        type="button"
        class="ui-field__toggle"
        :aria-pressed="revealed ? 'true' : 'false'"
        :aria-label="revealed ? m.auth.hidePassword : m.auth.showPassword"
        @click="revealed = !revealed"
      >
        {{ revealed ? m.auth.hide : m.auth.show }}
      </button>
    </div>
    <p v-if="hint" :id="`${id}-hint`" class="ui-field__hint">{{ hint }}</p>
    <p v-if="error" :id="`${id}-error`" class="ui-field__error">{{ error }}</p>
  </div>
</template>

<style scoped>
.ui-field {
  display: grid;
  gap: var(--space-1);
}
.ui-field__label {
  font-weight: 600;
  font-size: var(--text-sm);
}
.ui-field__control {
  display: flex;
  align-items: stretch;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
}
.ui-field__control:focus-within {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
.has-error .ui-field__control {
  border-color: var(--color-danger);
}
.ui-field__input {
  flex: 1;
  min-height: var(--touch-target);
  padding: 0 var(--space-3);
  border: 0;
  background: transparent;
  color: var(--color-text);
}
.ui-field__input:focus {
  outline: none;
}
.ui-field__toggle {
  padding: 0 var(--space-3);
  border: 0;
  border-left: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
}
.ui-field__hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
/* Error text stays light for contrast; the red border and ⚠ mark it (tokens.css rules). */
.ui-field__error {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
}
.ui-field__error::before {
  content: '⚠ ';
  color: var(--color-danger);
}
</style>

import { ref } from 'vue'
import { ApiError } from '@/api/client'
import { m } from '@/i18n'

/** Field errors for a form: client-side checks on blur, plus server errors after submit. */
export function useFieldErrors<F extends string>() {
  const fields = ref<Partial<Record<F, string>>>({})
  const form = ref<string | null>(null)

  function set(field: F, message: string | null) {
    fields.value = { ...fields.value, [field]: message ?? undefined }
  }

  function fromApi(error: unknown, known: readonly F[]) {
    if (!(error instanceof ApiError)) {
      form.value = m.errors.unexpected
      return
    }
    const next: Partial<Record<F, string>> = {}
    let mapped = false
    for (const [field, messages] of Object.entries(error.details)) {
      if ((known as readonly string[]).includes(field)) {
        next[field as F] = Array.isArray(messages) ? String(messages[0]) : String(messages)
        mapped = true
      }
    }
    fields.value = next
    form.value = mapped ? null : error.code === 'network_error' ? m.errors.network : error.message
  }

  function clear() {
    fields.value = {}
    form.value = null
  }

  const hasErrors = () => Object.values(fields.value).some(Boolean)

  return { fields, form, set, fromApi, clear, hasErrors }
}

export const validators = {
  email: (value: string) =>
    !value.trim()
      ? m.auth.errors.emailRequired
      : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
        ? null
        : m.auth.errors.emailInvalid,
  required: (value: string) => (value.trim() ? null : m.auth.errors.required),
  newPassword: (value: string) => (value.length >= 8 ? null : m.auth.errors.passwordShort),
  displayName: (value: string) =>
    !value.trim() ? m.auth.errors.required : value.length > 40 ? m.auth.errors.nameLong : null,
}

/** Only same-site paths are allowed as redirect targets (no `//host` or absolute URLs). */
export function safeNext(next: unknown, fallback = '/cases'): string {
  return typeof next === 'string' && next.startsWith('/') && !next.startsWith('//')
    ? next
    : fallback
}

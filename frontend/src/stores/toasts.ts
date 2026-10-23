import { defineStore } from 'pinia'
import { ref } from 'vue'

export const TOAST_TIMEOUT_MS = 6000 // UI_UX_GUIDELINES §6: auto-dismiss 6s, paused on hover/focus

export interface ToastInput {
  message: string
  tone?: 'info' | 'success' | 'discovery' | 'error'
  action?: { label: string; onClick: () => void }
}

export interface Toast extends Required<Pick<ToastInput, 'message' | 'tone'>> {
  id: number
  action?: ToastInput['action']
}

export const useToastStore = defineStore('toasts', () => {
  const toasts = ref<Toast[]>([])
  const timers = new Map<number, ReturnType<typeof setTimeout>>()
  let nextId = 1

  function schedule(id: number) {
    clearTimeout(timers.get(id))
    timers.set(
      id,
      setTimeout(() => dismiss(id), TOAST_TIMEOUT_MS),
    )
  }

  function push(input: ToastInput): number {
    const id = nextId++
    toasts.value.push({
      id,
      message: input.message,
      tone: input.tone ?? 'info',
      action: input.action,
    })
    schedule(id)
    return id
  }

  function dismiss(id: number) {
    clearTimeout(timers.get(id))
    timers.delete(id)
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function pause(id: number) {
    clearTimeout(timers.get(id))
    timers.delete(id)
  }

  function resume(id: number) {
    if (toasts.value.some((t) => t.id === id)) schedule(id)
  }

  return { toasts, push, dismiss, pause, resume }
})

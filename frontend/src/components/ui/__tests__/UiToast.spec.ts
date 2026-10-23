import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import UiToastRegion from '../UiToastRegion.vue'
import { TOAST_TIMEOUT_MS, useToastStore } from '@/stores/toasts'
import { axeViolations, describeViolations } from '@/test/a11y'

describe('toasts', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })
  afterEach(() => vi.useRealTimers())

  function mountRegion() {
    return mount(UiToastRegion, { attachTo: document.body })
  }

  it('renders pushed toasts inside a polite live region', async () => {
    const w = mountRegion()
    useToastStore().push({ message: 'New evidence: Courier Confirmation' })
    await nextTick()
    const region = w.find('[aria-live="polite"]')
    expect(region.exists()).toBe(true)
    expect(region.text()).toContain('New evidence: Courier Confirmation')
  })

  it('auto-dismisses after the timeout', async () => {
    const w = mountRegion()
    useToastStore().push({ message: 'Saved' })
    await nextTick()
    vi.advanceTimersByTime(TOAST_TIMEOUT_MS + 10)
    await nextTick()
    expect(w.text()).not.toContain('Saved')
  })

  it('pauses auto-dismiss while hovered', async () => {
    const w = mountRegion()
    useToastStore().push({ message: 'Hold on' })
    await nextTick()
    await w.find('.ui-toast').trigger('mouseenter')
    vi.advanceTimersByTime(TOAST_TIMEOUT_MS * 2)
    await nextTick()
    expect(w.text()).toContain('Hold on')
    await w.find('.ui-toast').trigger('mouseleave')
    vi.advanceTimersByTime(TOAST_TIMEOUT_MS + 10)
    await nextTick()
    expect(w.text()).not.toContain('Hold on')
  })

  it('can be dismissed with its button, and runs its action', async () => {
    const onAction = vi.fn<() => void>()
    const w = mountRegion()
    useToastStore().push({ message: 'New evidence', action: { label: 'View', onClick: onAction } })
    await nextTick()
    await w.find('.ui-toast__action').trigger('click')
    expect(onAction).toHaveBeenCalledOnce()
    useToastStore().push({ message: 'Another' })
    await nextTick()
    await w.find('button[aria-label="Dismiss"]').trigger('click')
    expect(w.text()).not.toContain('Another')
  })

  it('has no axe violations', async () => {
    const w = mountRegion()
    useToastStore().push({ message: 'Saved', tone: 'success' })
    await nextTick()
    vi.useRealTimers()
    const v = await axeViolations(w.element)
    expect(v, describeViolations(v)).toEqual([])
  })
})

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import UiDialog from '../UiDialog.vue'
import { axeViolations, describeViolations } from '@/test/a11y'

function mountDialog(props: Record<string, unknown> = {}) {
  return mount(UiDialog, {
    props: { open: false, title: 'Flag a contradiction', ...props },
    slots: {
      default: '<p>Pick a statement.</p>',
      footer: '<button type="button">Flag it</button>',
    },
    attachTo: document.body,
  })
}

describe('UiDialog', () => {
  it('opens as a modal when open becomes true, labelled by its title', async () => {
    const w = mountDialog()
    const dialog = w.find('dialog')
    expect(dialog.attributes('open')).toBeUndefined()
    await w.setProps({ open: true })
    await nextTick()
    expect(dialog.attributes('open')).toBeDefined()
    const titleId = dialog.attributes('aria-labelledby')!
    expect(w.find(`#${titleId}`).text()).toBe('Flag a contradiction')
  })

  it('requests closing via the close button', async () => {
    const w = mountDialog({ open: true })
    await nextTick()
    await w.find('button[aria-label="Close"]').trigger('click')
    expect(w.emitted('update:open')?.[0]).toEqual([false])
  })

  it('requests closing on Escape (native cancel event)', async () => {
    const w = mountDialog({ open: true })
    await nextTick()
    await w.find('dialog').trigger('cancel')
    expect(w.emitted('update:open')?.[0]).toEqual([false])
  })

  it('renders as a sheet variant', () => {
    expect(mountDialog({ variant: 'sheet' }).find('dialog').classes()).toContain('ui-dialog--sheet')
  })

  it('has no axe violations when open', async () => {
    const w = mountDialog({ open: true })
    await nextTick()
    const v = await axeViolations(w.element)
    expect(v, describeViolations(v)).toEqual([])
  })
})

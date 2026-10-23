import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import UiButton from '../UiButton.vue'
import UiIconButton from '../UiIconButton.vue'
import { axeViolations, describeViolations } from '@/test/a11y'

describe('UiButton', () => {
  it('renders its label, defaults to type="button" and the secondary variant', () => {
    const w = mount(UiButton, { slots: { default: 'Visit' } })
    expect(w.text()).toContain('Visit')
    expect(w.attributes('type')).toBe('button')
    expect(w.classes()).toContain('ui-button--secondary')
  })

  it('emits click', async () => {
    const w = mount(UiButton, { slots: { default: 'Go' } })
    await w.trigger('click')
    expect(w.emitted('click')).toHaveLength(1)
  })

  it('is busy: announces it, keeps focusability, and swallows clicks', async () => {
    const w = mount(UiButton, { props: { busy: true }, slots: { default: 'Saving' } })
    expect(w.attributes('aria-busy')).toBe('true')
    expect(w.attributes('aria-disabled')).toBe('true')
    expect(w.attributes('disabled')).toBeUndefined()
    await w.trigger('click')
    expect(w.emitted('click')).toBeUndefined()
  })

  it('does not emit click when disabled', async () => {
    const w = mount(UiButton, { props: { disabled: true }, slots: { default: 'No' } })
    await w.trigger('click')
    expect(w.emitted('click')).toBeUndefined()
  })

  it.each(['primary', 'secondary', 'ghost', 'danger'] as const)(
    'supports variant %s',
    (variant) => {
      const w = mount(UiButton, { props: { variant }, slots: { default: 'x' } })
      expect(w.classes()).toContain(`ui-button--${variant}`)
    },
  )

  it('has no axe violations', async () => {
    const w = mount(UiButton, { slots: { default: 'Begin' }, attachTo: document.body })
    const v = await axeViolations(w.element)
    expect(v, describeViolations(v)).toEqual([])
  })
})

describe('UiIconButton', () => {
  it('uses its label as the accessible name and hides the icon', () => {
    const w = mount(UiIconButton, {
      props: { label: 'Close' },
      slots: { default: '<svg data-test="icon"></svg>' },
    })
    expect(w.attributes('aria-label')).toBe('Close')
    expect(w.find('[aria-hidden="true"]').exists()).toBe(true)
  })

  it('emits click and has no axe violations', async () => {
    const w = mount(UiIconButton, {
      props: { label: 'Open notebook' },
      slots: { default: '✎' },
      attachTo: document.body,
    })
    await w.trigger('click')
    expect(w.emitted('click')).toHaveLength(1)
    const v = await axeViolations(w.element)
    expect(v, describeViolations(v)).toEqual([])
  })
})

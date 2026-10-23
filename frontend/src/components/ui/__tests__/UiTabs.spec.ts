import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import UiTabs from '../UiTabs.vue'
import { axeViolations, describeViolations } from '@/test/a11y'

const tabs = [
  { id: 'interview', label: 'Interview' },
  { id: 'profile', label: 'Profile' },
  { id: 'topics', label: 'Topics' },
]

function mountTabs(modelValue = 'interview') {
  return mount(UiTabs, {
    props: { tabs, modelValue, label: 'Suspect profile', 'onUpdate:modelValue': () => {} },
    slots: { default: ({ selected }: { selected: string }) => `Panel: ${selected}` },
    attachTo: document.body,
  })
}

describe('UiTabs', () => {
  it('follows the ARIA tabs pattern', () => {
    const w = mountTabs()
    expect(w.find('[role="tablist"]').attributes('aria-label')).toBe('Suspect profile')
    const tabEls = w.findAll('[role="tab"]')
    expect(tabEls).toHaveLength(3)
    expect(tabEls[0]!.attributes('aria-selected')).toBe('true')
    expect(tabEls[0]!.attributes('tabindex')).toBe('0')
    expect(tabEls[1]!.attributes('tabindex')).toBe('-1')
    const panel = w.find('[role="tabpanel"]')
    expect(panel.attributes('aria-labelledby')).toBe(tabEls[0]!.attributes('id'))
    expect(panel.text()).toBe('Panel: interview')
  })

  it('selects on click', async () => {
    const w = mountTabs()
    await w.findAll('[role="tab"]')[1]!.trigger('click')
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['profile'])
  })

  it.each([
    ['ArrowRight', 'interview', 'profile'],
    ['ArrowLeft', 'interview', 'topics'],
    ['End', 'interview', 'topics'],
    ['Home', 'topics', 'interview'],
    ['ArrowRight', 'topics', 'interview'],
  ])('%s from %s selects %s', async (key, from, to) => {
    const w = mountTabs(from)
    const current = w.findAll('[role="tab"]').find((t) => t.attributes('aria-selected') === 'true')!
    await current.trigger('keydown', { key })
    expect(w.emitted('update:modelValue')?.[0]).toEqual([to])
  })

  it('has no axe violations', async () => {
    const v = await axeViolations(mountTabs().element)
    expect(v, describeViolations(v)).toEqual([])
  })
})

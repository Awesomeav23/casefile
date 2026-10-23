import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import UiBadge from '../UiBadge.vue'
import UiCard from '../UiCard.vue'
import UiEmptyState from '../UiEmptyState.vue'
import UiSkeleton from '../UiSkeleton.vue'
import { axeViolations, describeViolations } from '@/test/a11y'

async function expectAccessible(element: Element) {
  const v = await axeViolations(element)
  expect(v, describeViolations(v)).toEqual([])
}

describe('UiCard', () => {
  it('renders on ink by default and on paper when asked', () => {
    expect(mount(UiCard, { slots: { default: 'x' } }).classes()).toContain('ui-card--ink')
    const paper = mount(UiCard, { props: { surface: 'paper', as: 'article' } })
    expect(paper.classes()).toContain('ui-card--paper')
    expect(paper.element.tagName).toBe('ARTICLE')
  })

  it('has no axe violations', async () => {
    await expectAccessible(
      mount(UiCard, { slots: { default: '<p>Body</p>' }, attachTo: document.body }).element,
    )
  })
})

describe('UiBadge', () => {
  it.each(['neutral', 'accent', 'danger', 'verified', 'new'] as const)(
    'supports tone %s',
    (tone) => {
      const w = mount(UiBadge, { props: { tone }, slots: { default: 'New' } })
      expect(w.classes()).toContain(`ui-badge--${tone}`)
      expect(w.text()).toBe('New')
    },
  )

  it('has no axe violations', async () => {
    await expectAccessible(
      mount(UiBadge, { slots: { default: 'Solved' }, attachTo: document.body }).element,
    )
  })
})

describe('UiSkeleton', () => {
  it('is hidden from assistive technology and renders the requested lines', () => {
    const w = mount(UiSkeleton, { props: { lines: 3 } })
    expect(w.attributes('aria-hidden')).toBe('true')
    expect(w.findAll('.ui-skeleton__line')).toHaveLength(3)
  })
})

describe('UiEmptyState', () => {
  it('renders title, body and action slot', () => {
    const w = mount(UiEmptyState, {
      props: { title: 'Nothing here yet', body: 'Visit a location to start.' },
      slots: { action: '<button type="button">Browse</button>' },
    })
    expect(w.find('h2').text()).toBe('Nothing here yet')
    expect(w.text()).toContain('Visit a location to start.')
    expect(w.find('button').exists()).toBe(true)
  })

  it('supports a custom heading level and has no axe violations', async () => {
    const w = mount(UiEmptyState, {
      props: { title: 'No cases', headingLevel: 3 },
      attachTo: document.body,
    })
    expect(w.find('h3').exists()).toBe(true)
    await expectAccessible(w.element)
  })
})

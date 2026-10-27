import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import UiTextField from '../UiTextField.vue'
import { axeViolations, describeViolations } from '@/test/a11y'

function field(props: Record<string, unknown> = {}) {
  return mount(UiTextField, {
    props: { label: 'Email', modelValue: '', ...props },
    attachTo: document.body,
  })
}

describe('UiTextField', () => {
  it('labels its input and reports edits', async () => {
    const w = field({ type: 'email', autocomplete: 'email' })
    const input = w.find('input')
    expect(w.find(`label[for="${input.attributes('id')}"]`).text()).toBe('Email')
    expect(input.attributes('type')).toBe('email')
    expect(input.attributes('autocomplete')).toBe('email')
    await input.setValue('sam@example.com')
    expect(w.emitted('update:modelValue')?.[0]).toEqual(['sam@example.com'])
  })

  it('marks errors invalid and links them to the input', () => {
    const w = field({ error: 'Enter a valid email.', hint: 'We never share it.' })
    const input = w.find('input')
    expect(input.attributes('aria-invalid')).toBe('true')
    const describedBy = input.attributes('aria-describedby')!.split(' ')
    const texts = describedBy.map((id) => w.find(`#${id}`).text())
    expect(texts).toEqual(['We never share it.', 'Enter a valid email.'])
  })

  it('emits blur for on-blur validation', async () => {
    const w = field()
    await w.find('input').trigger('blur')
    expect(w.emitted('blur')).toHaveLength(1)
  })

  it('lets a password be shown and hidden', async () => {
    const w = field({ label: 'Password', type: 'password' })
    const toggle = w.find('button')
    expect(w.find('input').attributes('type')).toBe('password')
    expect(toggle.attributes('aria-pressed')).toBe('false')
    await toggle.trigger('click')
    expect(w.find('input').attributes('type')).toBe('text')
    expect(toggle.attributes('aria-pressed')).toBe('true')
  })

  it('has no axe violations, with or without an error', async () => {
    for (const props of [{}, { error: 'Required.' }, { type: 'password', label: 'Password' }]) {
      const v = await axeViolations(field(props).element)
      expect(v, describeViolations(v)).toEqual([])
    }
  })
})

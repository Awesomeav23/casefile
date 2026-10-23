import { describe, expect, it } from 'vitest'
import { axeViolations } from '../a11y'

describe('axe helper', () => {
  it('really reports violations (guards against vacuous passes)', async () => {
    document.body.innerHTML = '<main><button type="button"></button><img src="x.png"></main>'
    const ids = (await axeViolations(document.body)).map((v) => v.id)
    expect(ids).toContain('button-name')
    expect(ids).toContain('image-alt')
  })
})

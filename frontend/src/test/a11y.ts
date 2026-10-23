import axe from 'axe-core'

/**
 * Run axe-core on a mounted element. Contrast is checked by the token contrast test instead
 * (jsdom can't compute styles), and "region" is irrelevant for components rendered alone.
 */
export async function axeViolations(element: Element): Promise<axe.Result[]> {
  const results = await axe.run(element, {
    rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
  })
  return results.violations
}

export function describeViolations(violations: axe.Result[]): string {
  return violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length} nodes)`).join('\n')
}

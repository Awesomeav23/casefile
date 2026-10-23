/**
 * WCAG 2.2 AA contrast for every token pairing the UI uses (docs/UI_UX_GUIDELINES.md §2).
 * 4.5:1 for normal text, 3:1 for large text and UI boundaries (focus rings, borders, icons).
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// Vitest stubs CSS imports (even ?raw), so read the file from disk; cwd is frontend/.
const css = readFileSync(resolve(process.cwd(), 'src/styles/tokens.css'), 'utf8')

function token(name: string): string {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`))
  if (!match?.[1]) throw new Error(`token --${name} not found as a hex colour`)
  return match[1]
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi! + 0.05) / (lo! + 0.05)
}

const TEXT = 4.5
const UI = 3

// [foreground, background, minimum ratio, where it's used]
const pairs: [string, string, number, string][] = [
  ['fog-100', 'ink-900', TEXT, 'body text on app background'],
  ['fog-100', 'ink-800', TEXT, 'text on rails / top bar'],
  ['fog-100', 'ink-700', TEXT, 'text on raised panels'],
  ['fog-300', 'ink-900', TEXT, 'secondary text on background'],
  ['fog-300', 'ink-800', TEXT, 'secondary text on rails'],
  ['fog-300', 'ink-700', TEXT, 'secondary text on panels'],
  ['paper-ink', 'paper-100', TEXT, 'document text'],
  ['paper-ink', 'paper-200', TEXT, 'text on nested paper'],
  ['paper-ink-muted', 'paper-100', TEXT, 'secondary document text'],
  ['ink-900', 'brass-400', TEXT, 'primary button label'],
  ['brass-400', 'ink-900', TEXT, 'active nav / accent text on background'],
  ['brass-400', 'ink-800', TEXT, 'active nav text on rail'],
  ['brass-400', 'ink-900', UI, 'focus ring on background'],
  ['brass-600', 'paper-100', UI, 'focus ring / accent boundary on paper'],
  ['tag-red-500', 'ink-900', UI, 'contradiction / danger icon and border'],
  ['tag-red-500', 'ink-800', UI, 'danger (outline) button border on rail'],
  ['ink-400', 'ink-900', UI, 'input border on background'],
  ['ink-400', 'ink-800', UI, 'input border on rail'],
  ['ink-400', 'ink-700', UI, 'input border on raised panel'],
  ['verified-500', 'ink-900', UI, 'verified timeline event'],
  ['claimed-400', 'ink-900', UI, 'claimed timeline event outline'],
  ['ink-600', 'ink-900', 1, 'decorative divider (not a required boundary)'],
]

describe('token contrast (WCAG AA)', () => {
  it.each(pairs)('%s on %s ≥ %s (%s)', (fg, bg, min) => {
    expect(contrast(token(fg), token(bg))).toBeGreaterThanOrEqual(min)
  })
})

# Casefile: UI/UX Guidelines

**Status:** Planning draft. Values are starting points to refine in the design-system milestone (M2). Font choices are subject to a legibility check.
**Related:** [SCREEN_DESIGN](SCREEN_DESIGN.md) · [PRODUCT_SPEC §7](PRODUCT_SPEC.md#7-user-experience-principles)

## 1. Visual direction: "Lamplight Archive"

The interface is a detective's desk at night: dark wood-and-ink surroundings, warm lamplight, paper documents, photographs, typewritten records, and a corkboard. Atmosphere appears in **surfaces, typography, and transitions**, never at the cost of reading comfort or speed.

Principles:
1. **Paper for content, ink for chrome.** Navigation and controls sit on dark ink surfaces. Readable content (documents, statements, briefings) sits on warm paper surfaces with dark text.
2. **One accent, used for meaning.** Brass/amber marks interactive focus and primary actions. Red ("evidence-tag red") is reserved for contradictions and destructive actions.
3. **Texture is subtle.** Noise and paper grain stay at ≤ 4% opacity. Content never sits on a photograph.
4. **Every flourish has an off switch.** Typewriter reveals, stamps, and page turns respect reduced motion and can be skipped.

## 2. Color tokens

Defined as CSS custom properties in `styles/tokens.css`. The dark theme is the default. A light "daylight" theme can be added by remapping tokens (D-08).

| Token | Value (dark) | Use |
|---|---|---|
| `--ink-900` | `#121316` | App background |
| `--ink-800` | `#1A1C21` | Rails, top bar |
| `--ink-700` | `#24272E` | Raised panels, cards on ink |
| `--ink-600` | `#323640` | Borders, dividers on ink |
| `--fog-300` | `#C9CCD3` | Secondary text on ink |
| `--fog-100` | `#EEF0F3` | Primary text on ink |
| `--paper-100` | `#F4EEDF` | Document/paper surface |
| `--paper-200` | `#E8DFC8` | Paper edge, nested paper |
| `--paper-ink` | `#2A2621` | Text on paper |
| `--paper-ink-muted` | `#5C554A` | Secondary text on paper |
| `--brass-400` | `#D9A441` | Primary action, focus ring, active nav |
| `--brass-600` | `#A87A22` | Primary action pressed / on paper |
| `--tag-red-500` | `#C8453B` | Contradictions, destructive |
| `--verified-500` | `#5E9C76` | Verified timeline events, success |
| `--claimed-400` | `#8FA3C7` | Claimed timeline events (always paired with dashed style) |
| `--cork-500` | `#7A5A3C` | Evidence board background (with texture) |

Rules:
- Text contrast: ≥ 4.5:1 for body text and ≥ 3:1 for large text and UI boundaries (WCAG 2.2 AA). Every pairing above is to be verified with a contrast checker in M2. Any that fail are adjusted, not excepted.
- **Color is never the only signal**: claimed vs. verified also differ by dashed vs. solid outline and an icon; correct and incorrect states also differ by icon and text.

## 3. Typography

| Role | Typeface (proposed) | Fallback stack | Use |
|---|---|---|---|
| Display | **Playfair Display** | Georgia, serif | Case titles, results stamp text, section headers (≥ 24px only) |
| Body / UI | **Inter** | system-ui, sans-serif | All UI, lists, forms |
| Document | **Source Serif 4** | Georgia, serif | Briefings, letters, documents on paper |
| Record | **IBM Plex Mono** | ui-monospace, monospace | Logs, timestamps, record tables, case numbers |

No novelty "typewriter" font is used for running text. A typewriter *feel* comes from the Plex Mono record style and letter-spacing on labels.

Type scale (rem, base 16px; scales with the user's text-size preference):

| Token | Size / line-height | Use |
|---|---|---|
| `--text-xs` | 0.75 / 1.4 | Badges, meta |
| `--text-sm` | 0.875 / 1.5 | Secondary UI |
| `--text-md` | 1 / 1.6 | Body |
| `--text-lg` | 1.125 / 1.6 | Document body |
| `--text-xl` | 1.375 / 1.4 | Card titles |
| `--text-2xl` | 1.75 / 1.25 | Section headers |
| `--text-3xl` | 2.5 / 1.1 | Case title |

Reading measure: document text is capped at 70ch.

## 4. Spacing, layout, shape

- **Spacing scale** (4px base): `--space-1` 4 · `2` 8 · `3` 12 · `4` 16 · `5` 24 · `6` 32 · `7` 48 · `8` 64.
- **Radii**: `--radius-sm` 4px (inputs, badges), `--radius-md` 8px (cards), `--radius-lg` 12px (dialogs). Paper documents use 2px radii with a soft shadow, because paper isn't rounded.
- **Elevation**: three shadow levels; paper uses a warm-tinted shadow.
- **Workspace grid**: left rail 220px (collapsible to 64px icons), content fluid, notebook drawer 360px.
- **Touch targets**: ≥ 44×44px on touch devices, ≥ 32px on pointer devices.

## 5. Iconography and imagery

- One outline icon set (proposed: Lucide), 1.5px stroke, 20px default.
- Case imagery is consistent per case (CASE_DESIGN §7). Portraits are shown in a "photo clipped to file" frame. Location images get a subtle vignette.
- Every image has alt text. Decorative textures are `aria-hidden`.

## 6. Reusable components

| Component | Notes |
|---|---|
| **Button** | Variants: primary (brass), secondary (outline), ghost, danger (tag-red). Sizes sm/md/lg. Busy state with spinner and preserved width |
| **IconButton** | Requires an accessible label |
| **Card** | On-ink and on-paper variants |
| **PaperDocument** | Renders document/correspondence/briefing Markdown on paper |
| **RecordView** | Monospace record/log renderer with optional row highlighting by the player |
| **PhotoViewer** | Zoom/pan, keyboard zoom (+/−), caption, alt text visible on demand |
| **EvidenceCard** | Thumbnail, title, kind badge, new badge, examined indicator |
| **PersonCard** | Portrait, name, role, suspect tag, suspicion marker |
| **StatementQuote** | Quote text, speaker, context; `⋯` menu actions |
| **Badge / Tag** | `new`, kind, difficulty, status ribbons |
| **Tabs**, **SegmentedControl** | |
| **Dialog / Sheet** | Focus-trapped; sheets on phone |
| **CommandPalette** | Global search |
| **Toast** | Discovery, saved, error; stacked; auto-dismiss 6s (pauses on hover/focus) |
| **ItemPicker** | Searchable picker over discovered items (used by present, cite, flag, board add) |
| **CitationChip** | Item reference chip that links to its source |
| **Stamp** | "CONTRADICTION", "CASE CLOSED", "UNSOLVED" animated stamp |
| **EmptyState**, **Skeleton**, **SaveIndicator** | |
| **TimelineLanes**, **BoardCanvas** | Complex components with list alternatives |

Components live in `components/ui` (primitives) and domain folders (ARCHITECTURE §4.1). Primitives contain no API calls.

## 7. Interaction feedback

| Moment | Feedback |
|---|---|
| Any action in flight | Control shows busy state; duplicate submits are blocked |
| New discovery | Toast + "new" badge + rail counter; screen-reader live announcement |
| Statement revealed | Typewriter reveal ≤ 600ms total, skippable; instant under reduced motion |
| Contradiction correct | "CONTRADICTION" stamp (300ms), explanation card, list of unlocks |
| Contradiction incorrect | Gentle shake (disabled under reduced motion) + "That doesn't hold up." No red flash |
| Board save | "Saving…" → "Saved" text indicator |
| Accusation submit | Full-screen hold (≤ 1.2s, skippable) → results reveal sequence |
| Errors | Plain-language message + next step; never raw codes |

**Motion**: durations 120–300ms, ease-out for entrances. `prefers-reduced-motion` or the in-app setting replaces motion with instant changes or fades.

**Sound**: none in v1.0 (D-12). If added later, it must be off by default, with a volume control.

## 8. Responsive behavior

| Breakpoint | Layout |
|---|---|
| Phone < 768px | Bottom tab bar; list→detail navigation; notebook full-screen; board and timeline default to list views; dialogs become sheets |
| Tablet 768–1199px | Collapsed icon rail; notebook as overlay drawer; board canvas usable with touch (pinch zoom, long-press to link) |
| Desktop ≥ 1200px | Full rail, 3-column interview room, notebook docked |

Content must reflow at 320px width and at 200% zoom without horizontal scrolling, except on the board canvas and the timeline canvas, which have list alternatives.

## 9. Accessibility (WCAG 2.2 AA target)

- **Keyboard**: everything is operable by keyboard. Focus order is logical, and a visible focus ring (2px brass + 2px offset) is always shown.
- **Shortcuts**: `⌘/Ctrl K` search, `N` new note, `G` then `E/P/T/B` go to section, `?` shortcut help. All are single-key shortcuts that can be disabled in settings (WCAG 2.1.4).
- **Drag alternatives** (WCAG 2.5.7): board cards move with arrow keys; links can be created via a menu; list view edits everything.
- **Screen readers**: landmarks per region; timeline and board have equivalent structured lists; live region for discoveries and results; images have meaningful alt text; the stamp animations have text equivalents.
- **Text**: user text size up to 130%, plus browser zoom to 200%. No text in images except case art, which has alt text.
- **Cognitive**: consistent placement of actions; no time pressure in v1.0 (D-15); the accusation requires explicit confirmation; autosave everywhere.
- **Clue accessibility**: every clue in an image is also available as text (CASE_DESIGN F7).

## 10. Voice and copy

- Second person, present tense, calm and dry: "You found 3 items in the Security Office."
- The game never editorialises about evidence ("Suspicious!"). It reports.
- Error copy is human: "We couldn't save your note. We'll keep trying."
- In-world documents use the voice of their in-world authors. UI copy stays neutral.

# Casefile: Testing Plan

**Status:** Planning draft. No tests exist yet, and none have been run. This document defines what will be tested and how.
**Related:** [ARCHITECTURE](ARCHITECTURE.md) · [CASE_DESIGN §6.6, §8](CASE_DESIGN.md) · [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md)

## 1. Strategy

| Layer | Tooling | Focus |
|---|---|---|
| Backend unit | pytest, pytest-django | Pure services: conditions, engine, validator, scoring |
| Backend integration / API | pytest-django + DRF `APIClient`, PostgreSQL (not SQLite) | Endpoints, permissions, transactions, constraints |
| Content | `validate_case` + pytest parametrised over `content/cases/*` | Every real case: schema, graph, fairness, walkthrough |
| Frontend unit / component | Vitest + Vue Test Utils (+ `@testing-library/vue` queries) | Stores, composables, components |
| Contract | OpenAPI schema diff + generated TS types compile | Frontend/backend agreement |
| End-to-end | Playwright (Chromium, Firefox, WebKit; one mobile viewport) | Real user journeys against a seeded backend |
| Accessibility | `@axe-core/playwright` + manual keyboard/screen-reader passes | WCAG 2.2 AA |
| Manual playtest | Protocol in §9 | Fairness and fun, which automated tests can't judge |

Test-first is the default for services (`conditions`, `engine`, `scoring`, `validator`). They are pure and their correctness is central.

**Fixtures:** a tiny synthetic case, `content/cases/_fixtures/mini-case/` (2 suspects, 2 locations, 4 evidence, 1 contradiction), keeps unit tests fast and spoiler-free. Real cases are tested by the content suite.

## 2. Backend unit tests

### 2.1 Condition evaluation (`play/conditions.py`)
- Each atom is true or false against fact sets (`start`, `visited`, `examined`, `asked`, `presented`, `contradiction`, `discovered`).
- Nested `all`/`any`; empty `all` is true; empty `any` is false (or rejected by the validator; decided in M3 and documented).
- Unknown atom → explicit error (never silently false).
- Property-style test: adding facts never turns a true condition false (monotonicity).

### 2.2 Discovery engine (`play/engine.py`)
- Initial discovery: start items only. Evidence with a `location` isn't discovered before a visit.
- Implicit `visited` is combined with an explicit `requires`.
- Chain unlocks within a single action (A → B → C) all resolve in one call (fixpoint).
- Idempotency: re-running the engine creates no duplicates.
- Topic availability requires its person to be discovered.
- Statements are revealed only by their topic or reaction trigger.

### 2.3 Actions (`play/actions.py`)
- Every action type: happy path, repeat (`repeat: true`, no new facts), and an undiscovered reference (`action_unavailable`).
- `present_evidence` without an authored reaction returns `default_reaction` and creates a fact.
- `flag_contradiction`: correct pairing, reversed pairing (statement/evidence order irrelevant), `accept_also` pairing, incorrect pairing (recorded, no discovery), already-found contradiction.

### 2.4 Scoring (`play/scoring.py`)
- Correct answer + full proof set → full points; correct + partial → half proof points; correct + no proof → answer points only; wrong answer + correct citations → 0 (proof only counts with a correct answer).
- A superset of citations containing a full set still counts.
- Tier thresholds: boundaries at exactly 0.9 and 0.7; per-case override.
- A wrong required question → `unsolved` regardless of score.
- `evidence`-kind questions score on proof only.

### 2.5 Validator (`content/validator.py`)
One failing fixture per rule:
- schema errors (missing required fields, bad enum);
- duplicate keys; dangling references in `requires`, statements, timeline sources, contradictions, answer keys;
- statement with both or neither trigger;
- timeline event without `requires`;
- an unreachable proof set (F1), unreachable key evidence (F2), orphan items (F3, warning only), a late-appearing culprit (F4), a suspect with no red-herring entry (F5), a failing walkthrough (F6);
- an image without alt text.

### 2.6 Importer (`content/importer.py`)
- First import creates all rows; re-import of identical content is a no-op (hash match).
- Text edit → updates in place, `content_version` unchanged.
- Added item → inserted; existing playthroughs discover it on their next action if its conditions are met.
- Removed key / changed answer key with an in-progress playthrough → refused. With `--force` → version bump, playthroughs marked `stale`.
- Import is transactional: a failure mid-import leaves no partial rows.
- Asset filenames are content-hashed; alt text is stored.

## 3. Database tests

Run against real PostgreSQL (CI service container):
- Unique constraints: `(case, key)` per content type; `(person, key)` for topics and statements; `(playthrough, item_type, item_key)` discovery; `(playthrough, kind, ref)` fact.
- **Partial unique index**: two `in_progress` playthroughs for the same user+case fail; `in_progress` + `accused` succeed.
- Check constraints: statement trigger exclusivity; timeline source exclusivity; `ends_at ≥ starts_at`; enum checks; `cite_min ≤ cite_max`.
- Cascades: account deletion removes all player data and leaves content intact; `PROTECT` prevents deleting a case with playthroughs.
- Migrations: `makemigrations --check` in CI (no missing migrations), plus a migrate-from-zero test.
- Concurrency: two simultaneous actions on one playthrough (threads with separate connections) produce consistent facts and no duplicate discoveries (row lock, ARCHITECTURE §3.3).

## 4. API tests

For **every endpoint**:
- Permission matrix: anonymous / other user / owner / staff → expected status (other user → **404**).
- Request validation errors use the envelope and the documented `code`.
- Response shape matches the OpenAPI schema (schema validation in tests).

Specific scenarios:
- Library shows only published cases to non-staff, and player status is correct for each state.
- Starting a playthrough: new → 201; existing in-progress → 200 same ID; `restart` → old one abandoned, new one created.
- Actions after accusation → 409.
- Board PUT with a stale version → 409 with current state; with an undiscovered ref → 400.
- Accusation: missing answers, invalid option, citation count out of range, undiscovered citation, missing `confirm`, second submission → each yields the right error; a valid submission freezes results and moves the playthrough to `accused`.
- Results before accusation → 409. After → full payload including undiscovered content.
- Rate limits on login and actions (with throttle rates lowered in test settings).
- CSRF: unsafe request without a token → 403.

## 5. Evidence-visibility and spoiler-leak tests (critical)

1. **Progressive leak test:** for each real case, replay the `walkthrough` step by step. After every step, fetch `casefile` and all other player endpoints and assert that:
   - every returned content key is in the playthrough's `Discovery` set;
   - no solution-only text appears in any response: answer-key explanations, the narrative, red-herring explanations, and the explanations of unfound contradictions (string search of the serialized JSON);
   - no undiscovered key appears anywhere, including in counts, IDs, or media URLs;
   - the `accusation-form` never includes `required_for_solve`, correct values, or points.
2. **Media URL test:** asset URLs for undiscovered evidence aren't derivable from keys (hashed names), and aren't present in responses.
3. **Serializer guard test:** a static test that fails if any player-facing serializer module imports a spoiler model (`AnswerKey`, `CaseSolution`, `RedHerring`, `Contradiction`). The one allowed path is via `visibility.py`.
4. **Staff-only fields:** `requires` appears only in staff preview playthroughs.

## 6. Mystery-logic validation (per real case)

Parametrised over every folder in `content/cases/` except those whose names start with `_` (`_fixtures`, `_template`), and run in CI on every change. The fixture cases have their own validator tests (§2.5):

| Test | Asserts |
|---|---|
| `test_case_validates` | `validate_case` reports zero errors |
| `test_case_solvable` | Exhaustive simulation reaches every `full` proof set for every question (F1) and every `key_evidence` / `cleared_by` item (F2) |
| `test_walkthrough_airtight` | Replaying the walkthrough via the **real API** (not just the engine) yields `solved` + `airtight` |
| `test_no_dead_ends` | From the state after *every* walkthrough step, the solution is still reachable (follows from monotonicity; asserted anyway) |
| `test_wrong_culprit_unsolved` | Accusing each non-culprit suspect, with otherwise-correct answers, yields `unsolved` |
| `test_red_herrings_clearable` | Every non-culprit suspect has reachable clearing evidence |
| `test_contradictions_discoverable` | Both sides of every contradiction (and every `accept_also`) are reachable before the contradiction itself |
| `test_timeline_consistency` | Every statement with a `claim` and each timeline event referencing it agree on times/location; times parse; events fall within the case's world date range |
| `test_option_wording` (warning) | Flags accusation options whose length differs from the median by > 60%, as a reviewer prompt for F9 |

## 7. Frontend tests

### 7.1 Stores and composables
- `playthrough` store merges `discovered` deltas without duplicates and keeps ordering; "new" flags and `seen` batching work.
- `useAction` blocks double submission, surfaces `ApiError`s, and triggers toasts on discovery.
- `board` store: debounced saves; a 409 triggers the conflict state; optimistic changes roll back on failure.
- `auth` store: 401 → redirect with `next`.
- API client: CSRF header on unsafe methods; error-envelope parsing; network error mapping.

### 7.2 Components
- EvidenceViewer renders each `kind` correctly; examine fires once.
- Interview room: asking renders statements; re-asking doesn't duplicate; the present-evidence picker lists only discovered evidence.
- Flag contradiction dialog: prefill from a statement or evidence; correct and incorrect result states.
- Timeline: claimed vs. verified styling + icons; list view equivalent content; keyboard navigation.
- Board: add, move (pointer and keyboard), link, delete; the list view edits the same model.
- Accusation: step validation (min/max citations), review summary, confirm dialog default focus is **not** Submit.
- Results: renders solved/unsolved variants; reduced-motion skips animation.
- Route guards: accused → results redirect; unauthenticated → login.

### 7.3 Type checking & lint
`vue-tsc --noEmit`, ESLint, and Prettier in CI. Generated API types must compile against the current schema.

## 8. End-to-end tests (Playwright)

Seeded with the fixture case and *The Missing Masterpiece* via `import_case` before the run. Database reset between specs.

| Spec | Journey |
|---|---|
| `auth.spec` | Register → logout → login → password reset request |
| `library.spec` | Filters, status ribbons, briefing CTA states |
| `golden-path.spec` | Full Missing Masterpiece walkthrough through the UI → Airtight results |
| `wrong-accusation.spec` | Accuse a red herring → Unsolved results show solution and missed evidence |
| `contradiction.spec` | Incorrect flag feedback, then correct flag → stamp + unlocked topic appears |
| `resume.spec` | Play partway → reload/log out/in → state, board, notes, theories intact |
| `restart.spec` | Start over → old playthrough abandoned, history shows both |
| `board.spec` | Pin from evidence viewer, keyboard move, link, list view, persistence |
| `conflict.spec` | Two tabs edit the board → second save shows reload prompt |
| `mobile.spec` | 390×844 viewport: tab bar, list board, timeline list, accusation |
| `a11y.spec` | axe scan with no serious/critical violations on every screen; keyboard-only golden path for the first 10 steps |
| `progress.spec` | After solving, progress shows the tier and history |

## 9. Manual playtest protocol (per case, before publish)

1. At least **two testers who didn't author the case**, playing independently without hints.
2. Record: time to solve, outcome and tier, incorrect flags, moments of confusion, and whether they felt the solution was fair (1–5) and satisfying (1–5).
3. **Publish gate:** at least one tester solves the case; median fairness ≥ 4; every "unfair" comment is resolved or explicitly accepted.
4. Accessibility spot check: one tester completes the case keyboard-only, and one with a screen reader (if possible).

## 10. CI pipeline (planned)

```
lint+typecheck (py: ruff, mypy optional; ts: eslint, vue-tsc)
  → backend tests (PostgreSQL service) incl. content suite
  → frontend unit/component tests
  → build SPA, generate schema, check TS types
  → e2e (Playwright, Chromium on every PR; all browsers nightly / on main)
```

Coverage targets (guidance, not gates): services ≥ 90%, overall backend ≥ 80%, frontend stores/composables ≥ 80%. **Gates:** the content suite and the spoiler-leak tests must pass. There are no exceptions to either.

## 11. Non-functional checks

- Performance: an action endpoint is p95 < 150 ms on a Hard case with a fully discovered playthrough (simple pytest-benchmark or Locust smoke test before launch).
- Payload: the casefile is < 200 KB for a fully discovered Hard case.
- Security: `manage.py check --deploy` clean; dependency audit (`pip-audit`, `npm audit`) in CI; session cookie flags verified in a deployment smoke test.
- Lighthouse on Landing/Library: performance ≥ 85, accessibility ≥ 95.

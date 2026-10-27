# Casefile: Testing Plan

**Status:** Planning draft. No tests exist yet, and none have been run. This document defines what will be tested and how.
**Related:** [ARCHITECTURE](ARCHITECTURE.md) · [CASE_DESIGN §6.7, §8](CASE_DESIGN.md) · [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md)

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

**Fixtures:** a tiny synthetic case, `content/cases/_fixtures/mini-case/` (2 suspects, 2 locations, 4 evidence, 1 contradiction, 2 hint tracks), keeps unit tests fast and spoiler-free. Real cases are tested by the content suite.

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
### 2.3a Contradiction flags (`play/flags.py`, D-03)
- Create: correct pairing → `confirmed` + `contradiction` fact + unlocks; reversed order and `accept_also` pairings also confirm; incorrect pairing → `unconfirmed`, no fact, no discovery.
- **No penalty:** incorrect flags change no score input; scoring and results stats contain no incorrect-flag count (asserted on the serialized payloads).
- Revise: changing an unconfirmed flag to a correct pairing confirms it; to another incorrect pairing keeps it unconfirmed and bumps `revision`.
- Remove: unconfirmed → deleted; confirmed → 409 `flag_locked`, and its fact and unlocks remain.
- Duplicate pairing → 409 `flag_exists`; a second confirmed flag for the same contradiction is impossible (partial unique index).

### 2.3b Hints (`play/hints.py`, D-04)
- A track is offered only when `requires` is met and `resolved_when` isn't; ordering by `priority`.
- Tiers reveal strictly in order; skipping to tier 3 is refused; tier 3 without `confirm` → 400 `confirmation_required`.
- After the track resolves, revealed tiers stay readable and no new tier can be revealed.
- No offered track → 409 `no_hint_available`.
- Hint use doesn't change score or tier (until D-21 says otherwise), but appears in results `hints_used`.

### 2.3c Guest identity & claiming (`accounts/identity.py`, `accounts/claim.py`, D-01)
- Browsing (library, briefing) creates no guest ID; starting a playthrough creates one lazily.
- Guest playthroughs are owner-scoped: another guest or a user gets 404.
- Claim on **register** and on **login** moves all guest playthroughs with their events, facts, discoveries, flags, hint reveals, notes, board, theories, and accusations; `guest_id` cleared; the `claimed` payload is correct.
- D-23 conflict: the account and the guest both have an in-progress playthrough of one case → the less recently active becomes `abandoned`, both appear in history, and `conflicts` reports it.
- Claiming is atomic: a failure mid-claim leaves the guest data untouched.
- Logout after a claim → the next guest start uses a new guest ID.
- `purge_guest_data`: deletes only guest playthroughs inactive longer than the retention period; never touches account-owned data; is idempotent.
- `DELETE /me/guest/` removes only the current guest's data.

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
- a hint track with ≠ 3 tiers or with `mentions` not guaranteed discovered when offered (F12); a proof-set contradiction with no covering track (F13, warning); hint text containing a correct option label or an `answer_terms` phrase (F14, warning);
- a `case.yaml` without `copyright` (D-20);
- an image without alt text.

### 2.5a Implemented in M3
- `play/tests/test_conditions.py`, `test_engine.py`, `test_scoring.py`: TESTING_PLAN §2.1, §2.2 (engine core), §2.4.
- `content/tests/test_validator.py`: the fixture is clean, the Masterpiece skeleton has no errors, the Mermaid output, and **one broken copy of the fixture per rule** (schema, YAML, duplicate keys, slug, conditions, references, assets, HTML, timeline, F1–F6, F12–F14, unreachable contradictions). Each asserts the rule and the file/key it names.
- `content/tests/test_validate_command.py`: exit codes, `--all` skipping `_` folders, `--mermaid`, `--strict`.

### 2.6 Importer (`content/importer.py`)
- First import creates all rows; re-import of identical content is a no-op (hash match).
- Text edit → updates in place, `content_version` unchanged.
- Added item → inserted; existing playthroughs discover it on their next action if its conditions are met.
- Removed key / changed answer key with an in-progress playthrough → refused. With `--force` → version bump, playthroughs marked `stale`.
- Import is transactional: a failure mid-import leaves no partial rows.
- Asset paths stored by the importer equal the paths produced by `collect_case_assets` (same deterministic hash function), so a build and a release step run separately still agree.

### 2.6a Implemented in M4
- `content/tests/test_importer.py`: everything in §2.6, plus effective `requires`, typed references, publish (with its history row), and the `import_case` / `collect_case_assets` commands.
- `content/tests/test_models.py`: content-table constraints from §3, plus `RESTRICT` on locations and cascade on case deletion.
- `content/tests/test_admin.py`: every content admin page loads, and adding content through the admin is refused.

## 3. Database tests

Run against real PostgreSQL (CI service container):
- Unique constraints: `(case, key)` per content type; `(person, key)` for topics and statements; `(playthrough, item_type, item_key)` discovery; `(playthrough, kind, ref)` fact.
- **Partial unique indexes**: two `in_progress` playthroughs for the same user+case (or the same guest+case) fail; `in_progress` + `accused` succeed; preview playthroughs are excluded.
- Ownership check: a playthrough with both or neither of `user_id` / `guest_id` is rejected.
- One accusation per playthrough (D-02): a second `play_accusation` row for a playthrough fails.
- Flags: duplicate pairing rejected; two confirmed flags for one contradiction rejected; the `contradiction_key` ⇔ `confirmed` check holds.
- Hint reveals: duplicate (playthrough, track, tier) rejected; exactly 3 tiers per imported track.
- Check constraints: statement trigger exclusivity; timeline source exclusivity; `ends_at ≥ starts_at`; enum checks; `cite_min ≤ cite_max`.
- Cascades: account deletion removes all player data (incl. flags and hint reveals) and leaves content intact; `PROTECT` prevents deleting a case with playthroughs.
- Migrations: `makemigrations --check` in CI (no missing migrations), plus a migrate-from-zero test.
- Concurrency: two simultaneous actions on one playthrough (threads with separate connections) produce consistent facts and no duplicate discoveries (row lock, ARCHITECTURE §3.3).

## 4. API tests

For **every endpoint**:
- Permission matrix: fresh visitor / guest (owner) / other guest / account (owner) / other account / staff → expected status. Non-owners always get **404**, and account-only endpoints return 401 for guests.
- Request validation errors use the envelope and the documented `code`.
- Response shape matches the OpenAPI schema (schema validation in tests).

Specific scenarios:
- Library shows only published cases to non-staff, and player status is correct for each state.
- Starting a playthrough: new → 201; existing in-progress → 200 same ID; `restart` → old one abandoned, new one created.
- Actions after accusation → 409.
- Board PUT with a stale version → 409 with current state; with an undiscovered ref → 400.
- Accusation: missing answers, invalid option, citation count out of range, undiscovered citation (`invalid_reference`), missing `confirm`, second submission (`accusation_already_submitted`, D-02) → each yields the right error; a valid submission freezes results and moves the playthrough to `accused`; actions, flags, and hint reveals afterwards → 409.
- Replay after accusation: `POST /cases/{slug}/playthroughs/` creates a new playthrough; the old result stays readable.
- Results before accusation → 409. After → full payload including undiscovered content.
- Rate limits on login, guest playthrough starts (per IP), actions/flags, and hint reveals (with throttle rates lowered in test settings).
- CSRF: unsafe request without a token → 403.

## 5. Evidence-visibility and spoiler-leak tests (critical)

1. **Progressive leak test:** for each real case, replay the `walkthrough` step by step. After every step, fetch `casefile` and all other player endpoints and assert that:
   - every returned content key is in the playthrough's `Discovery` set;
   - no solution-only text appears in any response: answer-key explanations, the narrative, red-herring explanations, and the explanations of unfound contradictions (string search of the serialized JSON);
   - no undiscovered key appears anywhere, including in counts, IDs, or media URLs;
   - the `accusation-form` never includes `required_for_solve`, correct values, or points;
   - **hint text** appears only for tiers the player has revealed, and never in `casefile` (only the `hints` summary); an offered track's `goal` appears only while the track is offered or after a tier is revealed;
   - the explanation of a contradiction appears only after a **confirmed** flag, never for an unconfirmed one.
   - Run the progressive test twice per case: once as a **guest** and once as an **account holder**.
2. **Media URL test:** asset URLs for undiscovered evidence aren't derivable from keys (hashed names), and aren't present in responses.
3. **Serializer guard test:** a static test that fails if any **player-facing serializer module** imports a spoiler model (`AnswerKey`, `CaseSolution`, `RedHerring`, `Contradiction`, `HintTrack`, `Hint`). Services may read spoiler models (`flags.py`, `hints.py`, `scoring.py`, `results.py`, `engine.py`), but serializers receive spoiler-derived text only through `visibility.py`, `hints.py`, and `results.py`, which are covered by the progressive leak test.
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
| `test_hints_cover_solution` | Every proof-set contradiction and key evidence item is covered by a hint track (F13); all hint `mentions` are discovered whenever offered (F12) |
| `test_hints_dont_reveal` (warning) | No tier contains a correct option label or `answer_terms` phrase (F14) |
| `test_hint_walkthrough` | Simulated "always take the next hint" player: following only tier-3 directions plus the cheapest available actions reaches an accusable state with every `full` proof set discovered |
| `test_option_wording` (warning) | Flags accusation options whose length differs from the median by > 60%, as a reviewer prompt for F9 |

## 7. Frontend tests

### 7.1 Stores and composables
- `playthrough` store merges `discovered` deltas without duplicates and keeps ordering; "new" flags and `seen` batching work.
- `useAction` blocks double submission, surfaces `ApiError`s, and triggers toasts on discovery.
- `board` store: debounced saves; a 409 triggers the conflict state; optimistic changes roll back on failure.
- `auth` store: distinguishes visitor / guest / account; 401 on account-only endpoints → redirect with `next`; claim result surfaces a notice once.
- `hints` store: lazy load; reveal flow; confirm before direction tier.
- API client: CSRF header on unsafe methods; error-envelope parsing; network error mapping.

### 7.2 Components
- EvidenceViewer renders each `kind` correctly; examine fires once.
- Interview room: asking renders statements; re-asking doesn't duplicate; the present-evidence picker lists only discovered evidence.
- Flag contradiction dialog: prefill from a statement or evidence; correct and incorrect result states; incorrect offers Change pairing / Remove; My flags list shows confirmed as locked and unconfirmed as editable, with no failure counts.
- Hint panel: suggested track first; tiers in order; direction confirm dialog; "no hint" generic copy.
- Guest banner / save prompts: dismissible, never block navigation.
- Timeline: claimed vs. verified styling + icons; list view equivalent content; keyboard navigation.
- Board: add, move (pointer and keyboard), link, delete; the list view edits the same model.
- Accusation: investigation review lists only discovered loose ends; step validation (min/max citations); answer review summary; confirm dialog default focus is **not** Submit.
- Results: renders solved/unsolved variants; reduced-motion skips animation.
- Route guards: accused → results redirect; guests can reach every play route; only the account settings section requires login.

### 7.2a Implemented in M2
- **Token contrast** (`src/styles/__tests__/contrast.spec.ts`): every colour pairing in use is checked against WCAG AA (4.5:1 text, 3:1 UI).
- **Accessibility helper** (`src/test/a11y.ts`): axe-core on mounted components. The `color-contrast` rule is off in jsdom (covered by the token test). A self-test proves the helper reports real violations.
- **Primitives**: behaviour plus axe tests for all 9 `Ui*` components. **Routes**: every screen renders, titles set, 404, skip link, no route requires an account, and axe on the app shell.
- **API client**: CSRF header on unsafe methods only, envelope → `ApiError`, non-envelope errors, network errors, 204, and the 401 hook.

### 7.3 Type checking & lint
`vue-tsc --build`, oxlint + ESLint, and Prettier in CI (and as pre-commit hooks). Generated API types must compile against the current schema.

## 7.4 Implemented in M5
- **Backend:**
  - `accounts/tests/test_identity.py`: browsing creates no guest; the first write creates one with a 90-day session; accounts win over a leftover guest ID; guest writes need CSRF.
  - `test_auth_api.py`: every auth endpoint, the permission matrix, throttles, CSRF with and without a token, and the reset-token lifecycle.
- **Frontend:** `UiTextField`, the auth store, `AppHeader`, and the login, register and reset views (axe included).
- **E2E:** `e2e/tests/auth.spec.ts`.

## 8. End-to-end tests (Playwright)

Run from `e2e/` (`npx playwright test`). Playwright starts Django (8020) and Vite (5190) against a separate `casefile_e2e` database. Specs use unique emails, so no reset is needed between runs. From M7, specs that need cases will seed the fixture case and every case under `content/cases/` via `import_case`.

| Spec | Journey |
|---|---|
| `guest.spec` | Fresh visitor plays without an account → reloads and resumes → registers → progress claimed and visible on Progress; second browser context logs in and sees it (cross-device) |
| `guest-conflict.spec` | Account has an in-progress case; guest in another context starts the same case → logs in → conflict notice, both in history |
| `auth.spec` | Register → logout → login → password reset request |
| `library.spec` | Filters, status ribbons, briefing CTA states |
| `golden-path.spec` | Full Missing Masterpiece walkthrough through the UI, **as a guest** → investigation review → single accusation → Airtight results → Replay starts a fresh playthrough |
| `wrong-accusation.spec` | Accuse a red herring → Unsolved results show solution and missed evidence |
| `contradiction.spec` | Incorrect flag → "doesn't hold up", saved as Not confirmed → revise it to the correct pairing → stamp + unlocked topic; remove another unconfirmed flag; confirmed flag can't be removed |
| `hints.spec` | Request nudge → pointer → confirm direction → follow it → track resolves; results list hints used; score unchanged vs. a no-hint run |
| `resume.spec` | Play partway → reload/log out/in → state, board, notes, theories intact |
| `restart.spec` | Start over → old playthrough abandoned, history shows both |
| `board.spec` | Pin from evidence viewer, keyboard move, link, list view, persistence |
| `conflict.spec` | Two tabs edit the board → second save shows reload prompt |
| `mobile.spec` | 390×844 viewport: tab bar, list board, timeline list, accusation |
| `a11y.spec` | axe scan with no serious/critical violations on every screen; keyboard-only golden path for the first 10 steps |
| `progress.spec` | After solving, progress shows the tier and history |

## 9. Manual playtest protocol (per case, before publish)

1. At least **two testers who didn't author the case**, playing independently. At least one plays **without hints**. The other may use hints and also rates whether each hint used helped without giving the answer away (1–5).
2. Record: time to solve, outcome and tier, incorrect flags (for content tuning only; never shown to players), hints used, moments of confusion, and whether they felt the solution was fair (1–5) and satisfying (1–5).
3. **Publish gate:** at least one tester solves the case without hints; median fairness ≥ 4; median hint-quality ≥ 4 (no hint judged to "give it away"); every "unfair" comment is resolved or explicitly accepted.
4. Accessibility spot check: one tester completes the case keyboard-only, and one with a screen reader (if possible).

## 10. CI pipeline (planned)

```
secret scan (gitleaks) + lint+typecheck (py: ruff, mypy optional; ts: eslint, vue-tsc)
  → backend tests (PostgreSQL service) incl. content suite
  → frontend unit/component tests
  → build SPA, generate schema, check TS types
  → e2e (Playwright, Chromium on every PR; all browsers nightly / on main)
```

**CI before trust (D-19):** CI runs only once the public GitHub repository exists (D-28). Until then, every milestone's checks are run locally (`pre-commit run --all-files`, `pytest`, `npm run test`, Playwright) and their output is recorded in the milestone notes. Automated checks aren't treated as passing until they've gone green on GitHub.

Coverage targets (guidance, not gates): services ≥ 90%, overall backend ≥ 80%, frontend stores/composables ≥ 80%. **Gates:** the content suite and the spoiler-leak tests must pass. There are no exceptions to either.

## 11. Non-functional checks

- Performance: an action endpoint is p95 < 150 ms on a Hard case with a fully discovered playthrough (simple pytest-benchmark or Locust smoke test before launch).
- Payload: the casefile is < 200 KB for a fully discovered Hard case.
- Security: `manage.py check --deploy` clean; dependency audit (`pip-audit`, `npm audit`) in CI; session cookie flags verified in a deployment smoke test; **secret scan** (`gitleaks`) over full git history before the first public push and in CI thereafter (D-19).
- Deployment smoke test on Render (M20): health endpoint, guest start + one action, login + claim, static/asset URLs resolve, cron command dry-run.
- Lighthouse on Landing/Library: performance ≥ 85, accessibility ≥ 95.

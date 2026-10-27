# Casefile: Development Roadmap

**Status:** M0–M4 complete (M4: 2026-10-26). All later milestones are planned and not started. Implementation resumes only when the owner explicitly asks.
**Related:** every other document. Feature tags (Essential/Optional) come from [PRODUCT_SPEC](PRODUCT_SPEC.md). Decisions `D-xx` (decided and open) are listed in [PRODUCT_SPEC §9](PRODUCT_SPEC.md#9-decisions).

The product vision (PRODUCT_SPEC) describes **everything Casefile should become**. This roadmap describes **the order in which to build it**. Milestones **M0–M20** make up v1.0: all Essential features (including guest play and hints), three complete cases, and deployment on Render. M21+ are post-1.0 Optional enhancements.

Each milestone is sized for one developer at roughly 2–8 working days. Each one ends in a working, tested, committed state. **"Tests pass" means they were run and seen passing**: locally until the public repo and CI exist (D-28), on GitHub CI afterwards.

---

## Dependency overview

```
M0 Repo ✓ ─► M0.1 Licensing & public repo ✓
   │
   ├─► M1 Backend base ─► M3 Content format+validator+hints schema ─► M4 Importer ─► M6 Library API
   │        │                                                            │
   │        └─► M5 Accounts (optional) + guest identity ─────────────────┤
   └─► M2 Frontend base + design tokens ─────────────────────────────────┤
                                                                         ▼
                     M7 Playthroughs (guest or account) + engine + actions + claim + purge
                                                                         │
          ┌───────────────┬──────────────────┬───────────────────────────┤
          ▼               ▼                  ▼
   M8 Library/Briefing  M9 Workspace:      M10 Interviews + contradiction flags
      UI (no sign-up    Locations+Evidence      (revise/remove, no penalties)
      wall)                 │                  │
                            └────────┬─────────┘
                                     ▼
                   M11 Timeline   M12 Board+Notes   M13 Theories
                                     │
                                     ▼
                M14 Investigation review, single accusation, scoring, results
                                     │
                                     ▼
                M15 Tiered hints
                                     │
                                     ▼
                M16 Progress, settings, accounts & guest experience
                                     │
                                     ▼
                M17 Full Missing Masterpiece content (+ hint tracks) + playtest
                                     │
                                     ▼
                M18 Cases 2 & 3 (content only: proves no-code case additions)
                                     │
                                     ▼
                M19 Polish: a11y audit, responsive, motion, performance
                                     │
                                     ▼
                M20 Render verification, deployment & launch  ═══► v1.0
                                     │
                                     ▼
                M21+ Optional enhancements
```

Content writing for *The Missing Masterpiece* (narrative, evidence text, hint tracks) can run **in parallel** from M3 onward. M17 is where it's finished and playtested, not where it starts.

---

## M0: Repository & tooling setup ✓ (completed 2026-10-23)
**Depends on:** nothing
**Delivered:** folder layout; pinned Python 3.13 / Node 22 (moved to 24 LTS in M2); `.gitignore`, `.editorconfig`, `.env.example` (placeholders only); Docker Compose PostgreSQL 16 on port 5436; pre-commit (hygiene hooks + ruff); GitHub Actions lint workflow; first local commit.
**Acceptance criteria:**
- ✓ A fresh clone + documented commands starts PostgreSQL locally (verified: container healthy, `select version()` returns 16.x).
- ✓ Lint passes locally (`pre-commit run --all-files`).
- ✓ README setup section contains only verified commands for this stage.
- ✓ CI workflow verified on GitHub in M0.1 (first run green).
- Note: eslint/prettier hooks were deferred to M2, when the frontend exists.

## M0.1: Licensing & public-repository preparation ✓ (completed 2026-10-23)
**Depends on:** M0
**Decisions:** D-19, D-20, D-25, D-27, D-28 (decided; the owner approved the push on 2026-10-23).
**Scope:**
- Add `LICENSE` (MIT, application code).
- Add `content/COPYRIGHT.md`: original case narratives, characters, dialogue, evidence text, hints, solutions, and original artwork are all rights reserved. Third-party assets follow `CREDITS.md`. Fixtures and `_template` are MIT.
- README "License" section explaining the split, including the `docs/` license statement (D-27), plus a **spoiler notice** (D-25).
- `content/README.md` with the spoiler warning and authoring pointer.
- Full-history secret scan (`gitleaks` v8.30.1 via Docker). Add a `secret-scan` job to CI.
- **When the owner asks (D-28):** create the public GitHub repository, push, confirm the CI lint job goes green, then enable branch protection requiring CI.
**Acceptance criteria:**
- `LICENSE`, `content/COPYRIGHT.md`, `content/README.md`, and the README license/spoiler sections exist and agree with PRODUCT_SPEC D-20, D-25, D-27 and CASE_DESIGN §7.1–7.2.
- Secret scan reports no findings. `.env` isn't tracked, and `.env.example` contains no real credentials.
- ✓ Repo: https://github.com/Awesomeav23/casefile (public). First CI run green: https://github.com/Awesomeav23/casefile/actions/runs/40008827214 (`secret-scan` + `lint`).
- ✓ Branch protection on `main`: requires `secret-scan` and `lint`; force pushes and deletion blocked; admin enforcement off for solo development.
- ✓ Secret scan (gitleaks v8.30.1): no leaks in history or working tree.

## M1: Backend foundation ✓ (completed 2026-10-23)
**Depends on:** M0 (M0.1 recommended first so CI covers this milestone)
**Scope:** Django project `casefile` with apps `accounts`, `content`, `play`; **custom user model** (email login); settings via environment (incl. `CSRF_TRUSTED_ORIGINS`); DRF configured (session auth, JSON only, custom exception handler with the error envelope); drf-spectacular schema endpoint; `/api/v1/health/`; pytest-django against PostgreSQL (local and CI).
**Optional spike (no paid resources without owner approval):** check Render's documented build environment against our pins (Python 3.13, Node 24, PostgreSQL 16) and pre-deploy command availability, as input to D-26.
**Acceptance criteria:**
- `migrate` from zero succeeds; `makemigrations --check` clean.
- `GET /api/v1/health/` returns 200 and DB status.
- A test confirms a thrown error is rendered in the documented envelope.
- `/api/v1/schema/` serves a valid OpenAPI document.
- A CI backend job with a PostgreSQL service is added and green on GitHub.

**Delivered:** Django 5.2.18 LTS (security support to April 2028; move to 6.2 LTS when it ships), DRF 3.18.3, drf-spectacular 0.30.0, psycopg 3.3.6, argon2 hashing; `accounts.User` (email login, case-insensitive unique email via a `Lower(email)` constraint, email-based admin forms); env-driven settings (`SECRET_KEY` required; secure cookies unless `DEBUG`); DRF JSON-only, session auth, deny-by-default permissions; error envelope handler; `/api/v1/health/`, `/api/v1/schema/`, `/api/v1/docs/` (DEBUG only); 25 pytest tests run locally and in CI. `check --deploy` hardening (HSTS, SSL redirect) is deferred to M20.
Optional Render spike: not done (no Render resources created).

## M2: Frontend foundation & design tokens ✓ (completed 2026-10-23)
**Depends on:** M0
**Scope:** Vite + Vue 3 + TS + Vue Router + Pinia; `tokens.css` and base styles from UI_UX_GUIDELINES; fonts; primitives (Button, IconButton, Card, Dialog/Sheet, Tabs, Badge, Toast, Skeleton, EmptyState); route skeleton for every screen in SCREEN_DESIGN §1 (placeholder views); UI strings externalised into a single messages module from the start (enables localisation later, M29); API client (`client.ts`) with CSRF + error mapping; Vite proxy to Django; Vitest + ESLint + Prettier + `vue-tsc` (added to pre-commit and CI); `api:types` script.
**Acceptance criteria:**
- All routes render placeholder views; unknown route → 404 view. No route requires an account except the account settings section (D-01).
- Primitives have component tests and pass axe checks in Vitest/jsdom where applicable.
- Token colour pairings verified for AA contrast. Any failures are adjusted and documented.
- `npm run api:types` generates types from the M1 schema and the project compiles.

**Delivered:** Vue 3.5, TypeScript 6, Vite 8, Vue Router 5, Pinia 4, Vitest 4 (create-vue 3.24 scaffold); self-hosted fonts (@fontsource); `tokens.css` + `base.css`; 9 primitives with behaviour tests and axe checks (plus a test proving the axe helper catches violations); placeholder views for all 21 screen routes, a 404, and a test that no route requires an account; `en.ts` message module; typed API client (CSRF header, error-envelope → `ApiError`, 401 hook, network errors); `api:types` via openapi-typescript (npm `overrides` lets it use TypeScript 6; its peer range only lists TS 5); CI `frontend` and `api-contract` jobs; 102 frontend tests.
**Changes made during M2:**
- **Node pin moved from 22 to 24 LTS.** The toolchain targets Node 24, Node 22 is in maintenance, and npm 10.9 (bundled with Node 22/23) has a peer-resolution bug that npm 11 fixes.
- **Contrast check results:**
  - Light text on `tag-red-500` is 4.21:1, so danger buttons and badges are outline style.
  - `ink-600` borders are 1.54:1, so `--ink-400` (`#707684`, ≥ 3:1) was added for input borders.
  - `brass-600` and `tag-red-500` are restricted to UI boundaries and large text (UI_UX_GUIDELINES §2).
- **Fixed dev ports:** Django 8010 and Vite 5180, because 8000 and 5173 clash with other local projects.

## M3: Case content format, validator & hint schema ✓ (completed 2026-10-23)
**Depends on:** M1
**Scope:** YAML schema models (`content/schema.py`) for format v1 (CASE_DESIGN §5, **including `spoilers/hints.yaml` §5.10 and the `copyright` field**); `play/conditions.py` (pure); the **pure discovery-engine core** in `play/engine.py` (facts → discovered set, no database; ARCHITECTURE §3.2); validator: references, defaults, graph simulation, fairness rules F1–F6 and **hint rules F12–F14** (F6 initially limited to engine-level walkthrough), Mermaid graph output; `manage.py validate_case`; fixture `mini-case` (with 2 hint tracks); `content/cases/_template/`; skeleton files for *The Missing Masterpiece* (enough to validate).
**Decide during milestone:** empty `any` semantics; whether Markdown subset is validated at import. (D-25 is decided: spoilers may be committed to the public repo, with warnings.)
**Acceptance criteria:**
- Validator unit tests for every rule in TESTING_PLAN §2.5 pass, including hint and copyright rules.
- `mini-case` validates clean; each deliberately broken fixture fails with a readable error that names the file and key.
- The Missing Masterpiece skeleton validates.

**Delivered:** `play/conditions.py`, `play/engine.py` (pure core: discover, available actions, exhaustive simulation, guaranteed-items and avoid-a-condition analysis), `play/scoring.py` (pure), `content/schema.py` (Pydantic 2.14), `loader.py` (PyYAML 6, duplicate keys rejected), `compile.py`, `validator.py` (structure checks; F1–F6; F12–F14; unreachable contradictions; Mermaid), `manage.py validate_case` (`--all`, `--mermaid`, `--strict`); fixture `_fixtures/mini-case`; `_template/`; *The Missing Masterpiece* skeleton (6 people, 6 locations, 13 evidence, 3 contradictions, 6 hint tracks, 12 timeline events), which validates with 0 errors and 0 warnings and has an Airtight walkthrough; 116 new backend tests (141 total); CI validates every case.
**Decided during milestone:**
- Empty `all`/`any` is an error.
- Raw HTML is rejected by the validator (the Markdown subset is enforced by the renderer later).
- Topics and timeline events gain implicit conditions: the topic's person, the event's source.
- Partial proof scores half, rounded down.
- Assets must be real WebP files.
- Duplicate YAML keys are an error.
- Pure scoring was pulled forward from M14, so F6 can check for an Airtight result.
## M4: Content models & importer ✓ (completed 2026-10-26)
**Depends on:** M3
**Decisions:** D-14 (open; default policy implemented).
**Scope:** all content and spoiler models (DATA_MODEL §3–4, incl. `content_hinttrack`, `content_hint`) with constraints; `import_case` (transactional upsert by key, content hash, `--all`, `--publish`, `--force` breaking-change policy); deterministic asset hashing shared with `collect_case_assets` (build-time asset copy, ARCHITECTURE §7); `CaseImport` audit; read-only Django admin for content.
**Acceptance criteria:**
- Importer tests from TESTING_PLAN §2.6 pass, including the breaking-change refusal and importer/`collect_case_assets` path agreement.
- DB constraint tests for content tables pass (TESTING_PLAN §3).
- Importing `mini-case` and the Masterpiece skeleton produces browsable admin records, including hint tracks.

**Delivered:** 16 content models (8 player-visible, 6 spoiler, `AccusationOption`, `CaseImport`) with database constraints; `content/assets.py` (deterministic hashed names + `collect_case_assets`); `content/importer.py` + `import_case` (`--all`, `--publish`, `--force`); breaking-change detection; read-only admin for all content; 55 new tests (196 backend total). Verified against the dev database: both cases import, re-import is a no-op, and publishing works.
**Decided during milestone:**
- Location foreign keys use `RESTRICT`, not `PROTECT`, so deleting a case still cascades.
- In-world times are stored as UTC `timestamptz`.
- Every `requires` column stores the effective condition.
- Drafts accept breaking changes; published cases need `--force` (M7 narrows this to cases with playthroughs in progress).
- Publishing is recorded in the import history.

## M5: Optional accounts & guest identity
**Depends on:** M1, M2 (for UI)
**Decisions:** **D-01** (decided: guest play, optional accounts); D-17 (open; console email backend until M20); D-22 (open; default 90-day guest cookie).
**Scope:** `accounts/identity.py` (`get_player`: account or lazily created guest ID in the anonymous session); register/login/logout/me/CSRF endpoints (`/auth/me/` reports user, guest, or neither); password reset and change (console email in dev); profile & preferences (guest preferences in `localStorage`); rate limiting; login/register/reset screens with the "keep your progress across devices" benefit copy; auth store (visitor / guest / account).
**Acceptance criteria:**
- Browsing creates no guest ID; the first write does (unit test).
- API permission matrix tests (visitor / guest / account / staff) pass; CSRF enforced for guests and accounts alike.
- E2E `auth.spec` passes.
- Session cookie flags set per environment; guest session lifetime matches D-22's default.

## M6: Case library & briefing API
**Depends on:** M4, M5
**Scope:** `GET /cases/`, `GET /cases/{slug}/` with player status for **guests and accounts**; `copyright` in the briefing; draft visibility for staff; filters.
**Acceptance criteria:**
- API tests: published-only visibility, filter behaviour, status per player state for both identity types (statuses beyond `not_started` are covered once M7 exists; stubbed here).
- Response shapes match API_PLAN §3.

## M7: Playthroughs, discovery engine, actions & guest claiming
**Depends on:** M4, M5
**Decisions:** D-01, D-23 (decided); D-22 (open; default purge period).
**Scope:** narrow the importer's breaking-change refusal to published cases **with in-progress playthroughs** (M4 refuses for any published case); play models (Playthrough with `user_id` **or** `guest_id`, `is_preview`; Event, Fact, Discovery) and both partial unique indexes; the engine's persistence wrapper around the M3 core; `actions.py`, `visibility.py`; endpoints: start/resume/restart, list, summary, casefile, actions, seen, heartbeat, abandon, `DELETE /me/guest/`; **`accounts/claim.py`**: claim on register/login by reassigning playthrough ownership (all child data follows), with the D-23 rule and the `claimed` response payload; **`purge_guest_data`** command; per-IP throttle on guest starts; row-level locking; read-only Django admin for playthroughs; staff preview + reveal-all; **spoiler-leak test harness** (TESTING_PLAN §5) running against `mini-case` as guest and as account holder.
**Acceptance criteria:**
- Engine/action unit tests (TESTING_PLAN §2.2–2.3) and guest/claim tests (§2.3c) pass.
- Partial unique index, ownership check, and concurrency tests pass.
- Spoiler-leak and serializer-guard tests pass for `mini-case` under both identity types.
- A scripted API-only playthrough of `mini-case` as a guest reaches all content, then is claimed on register with nothing lost.

## M8: Library, briefing & landing UI
**Depends on:** M2, M6, M7
**Scope:** Landing, Library (filters in URL), Briefing (CTA states incl. resume/restart; **Begin investigation works with no account**; "Log in to save across devices" link; copyright footer), "Continue investigation" for guests and accounts.
**Acceptance criteria:**
- Screens match SCREEN_DESIGN §3, §5, §6 including loading/empty/error states.
- No screen before or during a case requires sign-up (manual check + E2E).
- `library.spec` E2E passes.

## M9: Workspace shell, locations & evidence
**Depends on:** M7, M8
**Scope:** workspace shell (rail with new counters, top bar incl. Hint button slot, notebook drawer placeholder, search palette, discovery toasts + live region, guest banner placeholder); Overview (feed, leads, objective); Locations; Evidence list + viewer with all `kind` renderers (PaperDocument, RecordView, PhotoViewer, transcript); `useAction`; `seen` batching; heartbeat; staff preview UI (Draft ribbon in library, "Reveal all" and "Show unlock reasons" toolbar; SCREEN_DESIGN §12).
**Acceptance criteria:**
- Visiting/examining in the UI produces the same discoveries as the API tests.
- Search palette finds only discovered items; discovery feed lists actions with their discoveries; "new" badges clear via `seen` and stay cleared after reload (component + E2E checks).
- Staff preview: "Reveal all" discovers everything in a preview playthrough only, and "Show unlock reasons" displays each item's `requires`. Non-staff never see either (API + UI tests).
- Component tests for each evidence renderer.
- Keyboard operable; axe clean on these screens.

## M10: People, interviews & contradiction flags
**Depends on:** M9
**Decisions:** **D-03** (decided: no penalties; revise/remove); **D-24** (open; default: confirmed flags are permanent and listed).
**Scope:** People directory; suspect profile / interview room; topics; present-evidence picker; interview log; suspicion markers endpoint + UI; ItemPicker; **flags resource** (`play/flags.py`, `play_contradictionflag`; create/revise/remove; confirm on match); Flag dialog with correct state (Stamp) and incorrect state (Change pairing / Remove); **My flags** list (confirmed locked, unconfirmed editable, no failure counts); confirmed-contradictions list. **Spike:** board library evaluation (ARCHITECTURE §4.4), so M12 starts informed.
**Acceptance criteria:**
- Flag unit/API tests (TESTING_PLAN §2.3a) pass, including "no incorrect-flag count in any player payload".
- `contradiction.spec` E2E passes on `mini-case`.
- Re-asking doesn't duplicate log entries; default reactions are marked.
- Suspicion markers persist per playthrough, appear on person cards, and never affect any server response other than the marker itself.
- Board spike outcome recorded in ARCHITECTURE §4.4.

## M11: Timeline
**Depends on:** M9 (events come from discovered statements/evidence)
**Scope:** TimelineLanes (person lanes, claimed vs. verified, filters, zoom, keyboard nav, source popover) and TimelineList (phone/screen reader).
**Acceptance criteria:**
- Claimed/verified distinguishable without colour.
- Lane and list views render identical data (component test).
- No automatic overlap/conflict highlighting (spec check).

## M12: Evidence board & notebook
**Depends on:** M10 (spike result), M9
**Scope:** Board endpoint with version + reference validation; BoardCanvas (chosen approach), keyboard move/link, list view, autosave & conflict handling; "Pin" action everywhere. Notes CRUD API + notebook drawer with attachments and autosave.
**Acceptance criteria:**
- `board.spec` and `conflict.spec` E2E pass.
- Board fully operable by keyboard; list view edits the same model.
- Notes survive reload and conflict between tabs is handled.

## M13: Theories
**Depends on:** M12 (citation chips and pickers reused)
**Scope:** Theories API + list/editor UI; duplicate/discard/restore; "Use for accusation" hook (prefill implemented in M14).
**Acceptance criteria:**
- CRUD with version conflict handling tested.
- Theory views show no correctness signal anywhere (review checklist).

## M14: Investigation review, single accusation, scoring & results
**Depends on:** M7 (backend), M13 (prefill), M10 (citations of contradictions)
**Decisions:** **D-02** (decided: one final accusation; review first; reveal afterwards; replay allowed); D-15, D-21 (open; default: neither time nor hints affect score).
**Scope:** `scoring.py`, `results.py`; **prefill from a theory** ("Use for accusation" / "Start from this theory"); accusation-form, accusation, results endpoints (unique accusation per playthrough); **Investigation review** step (built from the casefile: confirmed contradictions, active theory, loose ends incl. unconfirmed flags); accusation flow UI (steps, citation picker, answer review, confirm with one-attempt copy); results screen with reveal sequence, breakdown, narrative, red herrings, contradictions, missed evidence, stats (no incorrect-flag count); **Replay** from results; redirect rules.
**Acceptance criteria:**
- Scoring unit tests (TESTING_PLAN §2.4) and accusation API tests pass, including second-submission refusal and post-accusation 409s for actions/flags.
- Results frozen at submission (test edits content after accusation → results unchanged).
- Replay creates a new playthrough; the earlier result stays reachable.
- Starting the accusation from a theory prefills the suspect and citations, and the player can still change everything before confirming.
- `mini-case` golden path (as guest) and wrong-accusation E2E pass.
- Spoiler-leak suite still passes (results only after accusation).

## M15: Tiered hints
**Depends on:** M14 (results show hint usage), M10 (tracks often resolve on contradictions), M4 (hint content imported)
**Decisions:** **D-04** (decided: optional tiered hints in v1.0); **D-21** (open; default no score effect).
**Scope:** `play/hints.py` (offered tracks from facts, priority, strict tier order, direction-tier confirmation); `play_hintreveal`; `GET/POST /hints/`; hints summary in casefile; HintButton (dot when available), HintPanel, HintTierCard; `hints_used` on results; leak tests for hint text; hint-quality rules in the playtest protocol.
**Acceptance criteria:**
- Hint unit/API tests (TESTING_PLAN §2.3b) pass.
- Spoiler-leak suite extended: no unrevealed tier text, and no non-offered track's goal, ever appears in a response.
- `hints.spec` E2E passes on `mini-case`, and score is identical with and without hints (D-21 default).
- Validator hint rules (F12–F14) run in the content suite.

## M16: Progress, settings, accounts & guest experience
**Depends on:** M14, M15
**Decisions:** D-01, D-23 (decided); D-22 (open; default).
**Scope:** `/me/progress/` for guests and accounts; Progress screen (completion history, in-progress, totals; guest variant with save prompt and retention note); Settings (text size, reduced motion, tips; account section: password change, data export, account deletion with cascade; guest section: forget my progress); guest banner, save prompts (workspace, results), claim notice after login/register; scheduling plan for `purge_guest_data` (local run documented; Render Cron Job set up in M20).
**Acceptance criteria:**
- `progress.spec`, `guest.spec` (incl. cross-device check after claim), and `guest-conflict.spec` E2E pass.
- Account deletion test confirms all player data removed, content intact.
- `/me/export/` returns all of the user's playthrough data (events, discoveries, flags, hint reveals, notes, board, theories, accusations) as JSON.
- Preferences apply app-wide for guests (localStorage) and accounts (profile).
- No prompt blocks play (manual review against SCREEN_DESIGN §2).

## M17: *The Missing Masterpiece*, complete
**Depends on:** M16 (all mechanics exist)
**Decisions:** D-16 (open; default tone), D-18 (open; tips default).
**Scope:** finish all content to Standard targets (CASE_DESIGN §6.1), **including 6–10 hint tracks** and the copyright line; commission/source and credit images (licenses compatible with a public repo); complete walkthrough; staff preview review; playtest protocol (TESTING_PLAN §9, incl. hint quality); contextual first-time tips.
**Acceptance criteria:**
- Full content suite (TESTING_PLAN §6, incl. hint tests) passes for this case.
- `golden-path.spec`, `wrong-accusation.spec`, and `hints.spec` pass on this case.
- Publish gate from the playtest protocol met (incl. median hint quality ≥ 4); reviewer checks F7–F11 and F15 recorded.

## M18: Cases 2 and 3 (content-only milestone)
**Depends on:** M17
**Decisions:** **D-05** (decided: three complete, distinct mysteries); D-16, D-18 (open).
**Scope:** design, write, validate, and playtest an **Introductory** case (different crime type; doubles as onboarding) and a **Hard** case (layered contradictions). Each has its own setting, cast, and hint tracks. **Rule: no application code changes** for these ordinary content additions. If a case genuinely needs a new mechanic, it goes through the extension process (ARCHITECTURE §8) as a separately scoped, separately approved task, and the roadmap is updated.
**Acceptance criteria:**
- Three published cases exist, each with a distinct crime type, setting, and difficulty; each passes the content suite and publish gate.
- The git diff for this milestone touches only `content/` (plus docs), or every code change is justified and approved through the extension process.

## M19: Polish, accessibility & performance
**Depends on:** M18
**Decisions:** D-08 (light theme), D-12 (audio), D-13 (phone support). All open, with defaults.
**Scope:** full WCAG 2.2 AA audit (keyboard, screen reader, contrast, zoom/reflow) incl. hint panel and flag flows; responsive pass at all breakpoints; motion polish + reduced-motion verification; empty/error states review; performance budget checks (TESTING_PLAN §11); copy review against voice guidelines; cross-browser E2E.
**Acceptance criteria:**
- `a11y.spec` and `mobile.spec` pass on all three cases; manual screen-reader pass documented.
- Lighthouse targets met; action p95 < 150 ms; casefile < 200 KB.
- Zero open "serious" UX issues from playtests.

## M20: Render verification, deployment & launch
**Depends on:** M19 (and M0.1: repo public with green CI)
**Decisions:** **D-07** (decided: Render); **D-26** (open; default one Web Service + Render PostgreSQL); D-17 (email provider), D-06 (confirm no payments).
**Scope:**
1. **Verify first, before creating any paid resource** (ARCHITECTURE §9.3 checklist): current Render pricing and free-tier limits for Web Service, PostgreSQL, and Cron Job; pre-deploy command availability; supported Python/Node/PostgreSQL versions; backups/PITR; custom domain and TLS; region. Record the findings and costs in a short deployment note, and get the owner's go-ahead.
2. `render.yaml` Blueprint; build command (SPA build, `collect_case_assets`, `collectstatic`); release step (`migrate`, `import_case --all`); start command (gunicorn); environment variables/secret files; `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` for the chosen domain.
3. Render Cron Job for `purge_guest_data` (D-22).
4. Email provider wired up for password reset (D-17).
5. Staging (if affordable) or a pre-launch production smoke environment; backup + restore drill; Sentry (optional); privacy policy (covering guest cookies and retention) and terms pages; content deploy procedure; launch checklist.
**Acceptance criteria:**
- Verification note completed and approved by the owner before any paid resource is created.
- Deployed environment passes the full E2E suite and the Render smoke test (TESTING_PLAN §11).
- Database restore from backup demonstrated once.
- The cron purge runs successfully in the deployed environment (dry-run then real).
- Release procedure documented in README and executed end-to-end for a content-only update.
- **v1.0 released.**

---

## Post-1.0: optional enhancements (M21+)

Order to be decided against player feedback. Each is independent unless noted.

| Milestone | Feature | Depends on / decision |
|---|---|---|
| M21 | Light "daylight" theme | D-08 |
| M22 | Achievements & detective rank | M16 |
| M23 | Shareable spoiler-free result cards / leaderboards | D-09 |
| M24 | Audio evidence & ambient sound | D-12; new evidence kind (extension process) |
| M25 | Image hotspots | Extension process (new action + condition atom) |
| M26 | Case series / seasons; "coming soon" teasers | Content + small library UI change |
| M27 | Theory comparison view; board grouping/export | M12, M13 |
| M28 | In-browser authoring tool / invited authors | D-10 |
| M29 | Localisation | Strings externalised since M2 |
| M30 | LLM-assisted free-text questioning mapped to authored topics | D-11 |
| ongoing | New cases | Content pipeline only (no code for ordinary cases, D-05) |

## Coverage check: Essential features → milestones

| PRODUCT_SPEC area | Milestone(s) |
|---|---|
| 5.1 Accounts (optional) & guest play | M5 (identity, auth), M7 (guest ownership, claim, purge), M16 (guest UX, account management) |
| 5.2 Library & briefing | M6, M8 |
| 5.3 Workspace (locations, evidence, notebook, search, feed) | M9, M12 |
| 5.4 People & interviews | M10 |
| 5.5 Contradictions (flags, no penalties, revise/remove) | M7 (engine), M10 (flags + UI) |
| 5.6 Timeline | M11 |
| 5.7 Evidence board | M12 |
| 5.8 Theories | M13 |
| 5.9 Investigation review, accusation & results | M14 |
| 5.10 Player progress | M16 |
| 5.11 Hints | M3 (format), M4 (import), M15 (mechanics + UI), M17–M18 (authored tracks) |
| 5.12 Content pipeline | M3, M4, M7 (preview), M9 (preview UI) |
| 5.13 Presentation | M2, M19 |
| 5.14 Launch content (three cases) | M17, M18 |
| Repository, licensing, CI (D-19, D-20) | M0 ✓, M0.1 |
| Deployment on Render (D-07) | M20 |

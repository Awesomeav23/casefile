# Casefile: Development Roadmap

**Status:** Planning draft. No milestone has started.
**Related:** every other document. Feature tags (Essential/Optional) come from [PRODUCT_SPEC](PRODUCT_SPEC.md). Open decisions `D-xx` are listed in PRODUCT_SPEC §9.

The product vision (PRODUCT_SPEC) describes **everything Casefile should become**. This roadmap describes **the order in which to build it**. Milestones M0–M19 make up v1.0 (all Essential features + three cases + deployment). M20+ are post-1.0 Optional enhancements.

Each milestone is sized for one developer at roughly 2–8 working days. Each one ends in a working, tested, committed state.

---

## Dependency overview

```
M0 Repo ─► M1 Backend base ─► M3 Content format+validator ─► M4 Importer ─► M6 Library API
   │            │                                                 │
   │            └─► M5 Auth ──────────────────────────────────────┤
   └─► M2 Frontend base + design tokens ──────────────────────────┤
                                                                  ▼
                                    M7 Playthrough + discovery engine + actions API
                                                                  │
          ┌───────────────┬──────────────┬────────────────────────┤
          ▼               ▼              ▼                        ▼
   M8 Library/Briefing  M9 Workspace:  M10 Interviews       (all need M7)
      UI               Locations+Evidence  + contradictions
                          │               │
                          └──────┬────────┘
                                 ▼
               M11 Timeline   M12 Board+Notes   M13 Theories
                                 │
                                 ▼
                     M14 Accusation, scoring, results
                                 │
                                 ▼
                     M15 Progress + settings + account
                                 │
                                 ▼
          M16 Full Missing Masterpiece content + playtest
                                 │
                                 ▼
          M17 Cases 2 & 3 (content only — proves the pipeline)
                                 │
                                 ▼
          M18 Polish: a11y audit, responsive, motion, performance
                                 │
                                 ▼
          M19 Deployment & launch readiness  ═══► v1.0
                                 │
                                 ▼
          M20+ Optional enhancements
```

Content writing for *The Missing Masterpiece* (narrative, evidence text) can run **in parallel** from M3 onward. M16 is where it's finished and playtested, not where it starts.

---

## M0: Repository & tooling setup
**Depends on:** nothing
**Scope:** monorepo layout (README §Planned layout); `.gitignore`, `.editorconfig`; pinned versions (Python, Node, PostgreSQL); Docker Compose for PostgreSQL; pre-commit (ruff, prettier, eslint); GitHub Actions skeleton running lint on empty projects; `.env.example`; license decision.
**Acceptance criteria:**
- A fresh clone + documented commands starts PostgreSQL locally.
- CI runs and passes lint on the skeleton.
- README setup section updated with real, verified commands for this stage.

## M1: Backend foundation
**Depends on:** M0
**Scope:** Django project `casefile` with apps `accounts`, `content`, `play`; **custom user model** (email login); settings via environment; DRF configured (session auth, JSON only, custom exception handler with the error envelope); drf-spectacular schema endpoint; `/api/v1/health/`; pytest-django against PostgreSQL in CI.
**Acceptance criteria:**
- `migrate` from zero succeeds; `makemigrations --check` clean in CI.
- `GET /api/v1/health/` returns 200 and DB status.
- A test confirms a thrown error is rendered in the documented envelope.
- `/api/v1/schema/` serves a valid OpenAPI document.

## M2: Frontend foundation & design tokens
**Depends on:** M0
**Scope:** Vite + Vue 3 + TS + Vue Router + Pinia; `tokens.css` and base styles from UI_UX_GUIDELINES; fonts; primitives (Button, IconButton, Card, Dialog/Sheet, Tabs, Badge, Toast, Skeleton, EmptyState); route skeleton for every screen in SCREEN_DESIGN §1 (placeholder views); UI strings externalised into a single messages module from the start (enables localisation later, M30); API client (`client.ts`) with CSRF + error mapping; Vite proxy to Django; Vitest + ESLint + `vue-tsc` in CI; `api:types` script.
**Acceptance criteria:**
- All routes render placeholder views; unknown route → 404 view.
- Primitives have component tests and pass axe checks in Vitest/jsdom where applicable.
- Token colour pairings verified for AA contrast. Any failures are adjusted and documented.
- `npm run api:types` generates types from the M1 schema and the project compiles.

## M3: Case content format & validator
**Depends on:** M1
**Scope:** YAML schema models (`content/schema.py`) for format v1 (CASE_DESIGN §5); `play/conditions.py` (pure); the **pure discovery-engine core** in `play/engine.py` (facts → discovered set, no database; ARCHITECTURE §3.2); validator: references, defaults, graph simulation, fairness rules F1–F6 (F6 initially limited to engine-level walkthrough), Mermaid graph output; `manage.py validate_case`; fixture `mini-case`; `content/cases/_template/`; skeleton files for *The Missing Masterpiece* (enough to validate).
**Decide during milestone:** empty `any` semantics; whether Markdown subset is validated at import.
**Acceptance criteria:**
- Validator unit tests for every rule in TESTING_PLAN §2.5 pass.
- `mini-case` validates clean; each deliberately broken fixture fails with a readable error that names the file and key.
- The Missing Masterpiece skeleton validates.

## M4: Content models & importer
**Depends on:** M3
**Scope:** all content and spoiler models (DATA_MODEL §3–4) with constraints; `import_case` (transactional upsert by key, content hash, asset hashing/copying, `--publish`, `--force` breaking-change policy); `CaseImport` audit; read-only Django admin for content.
**Acceptance criteria:**
- Importer tests from TESTING_PLAN §2.6 pass, including the breaking-change refusal.
- DB constraint tests for content tables pass (TESTING_PLAN §3).
- Importing `mini-case` and the Masterpiece skeleton produces browsable admin records.

## M5: Authentication & accounts
**Depends on:** M1, M2 (for UI)
**Requires decision:** **D-01** (guest play), **D-17** (email provider; console backend acceptable until M19).
**Scope:** register/login/logout/me/CSRF endpoints; password reset (console email in dev); profile & preferences; rate limiting; login/register/reset screens; auth store; route guards.
**Acceptance criteria:**
- API permission and validation tests pass; CSRF enforced.
- E2E `auth.spec` passes locally.
- Session cookie flags set per environment.

## M6: Case library & briefing API
**Depends on:** M4, M5
**Scope:** `GET /cases/`, `GET /cases/{slug}/` with player status; draft visibility for staff; filters.
**Acceptance criteria:**
- API tests: published-only visibility, filter behaviour, status per player state (statuses beyond `not_started` are covered once M7 exists; stubbed here).
- Response shapes match API_PLAN §3.

## M7: Playthroughs, discovery engine & actions
**Depends on:** M4, M5
**Scope:** play models (Playthrough incl. `is_preview`, Event, Fact, Discovery); the engine's persistence wrapper around the M3 core; `actions.py`, `visibility.py`; read-only Django admin for playthroughs; endpoints: start/resume/restart, list, summary, casefile, actions, seen, heartbeat, abandon; row-level locking; staff preview + reveal-all; **spoiler-leak test harness** (TESTING_PLAN §5) running against `mini-case`.
**Acceptance criteria:**
- Engine/action unit tests (TESTING_PLAN §2.2–2.3) pass.
- Partial unique index and concurrency tests pass.
- Spoiler-leak and serializer-guard tests pass for `mini-case`.
- A scripted API-only playthrough of `mini-case` reaches all content.

## M8: Library, briefing & landing UI
**Depends on:** M2, M6, M7
**Scope:** Landing, Library (filters in URL), Briefing (CTA states incl. resume/restart), "Continue investigation".
**Acceptance criteria:**
- Screens match SCREEN_DESIGN §3, §5, §6 including loading/empty/error states.
- `library.spec` E2E passes.

## M9: Workspace shell, locations & evidence
**Depends on:** M7, M8
**Scope:** workspace shell (rail with new counters, top bar, notebook drawer placeholder, search palette, discovery toasts + live region); Overview (feed, leads, objective); Locations; Evidence list + viewer with all `kind` renderers (PaperDocument, RecordView, PhotoViewer, transcript); `useAction`; `seen` batching; heartbeat; staff preview UI (Draft ribbon in library, "Reveal all" and "Show unlock reasons" toolbar; SCREEN_DESIGN §12).
**Acceptance criteria:**
- Visiting/examining in the UI produces the same discoveries as the API tests.
- Component tests for each evidence renderer.
- Keyboard operable; axe clean on these screens.

## M10: People, interviews & contradictions
**Depends on:** M9
**Scope:** People directory; suspect profile / interview room; topics; present-evidence picker; interview log; suspicion markers endpoint + UI; ItemPicker; Flag Contradiction dialog with correct/incorrect states and Stamp component; found-contradictions list. **Spike:** board library evaluation (ARCHITECTURE §4.4), so M12 starts informed.
**Requires decision:** **D-03** (incorrect flag penalty) affects copy only at this stage.
**Acceptance criteria:**
- `contradiction.spec` E2E passes on `mini-case`.
- Re-asking doesn't duplicate log entries; default reactions are marked.
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

## M14: Accusation, scoring & results
**Depends on:** M7 (backend), M13 (prefill), M10 (citations of contradictions)
**Requires decision:** **D-02** (attempts). Should be settled before starting. Default: one attempt.
**Scope:** `scoring.py`, `results.py`; accusation-form, accusation, results endpoints; accusation flow UI (steps, citation picker, review, confirm); results screen with reveal sequence, breakdown, narrative, red herrings, contradictions, missed evidence, stats; redirect rules.
**Acceptance criteria:**
- Scoring unit tests (TESTING_PLAN §2.4) and accusation API tests pass.
- Results frozen at submission (test edits content after accusation → results unchanged).
- `mini-case` golden path and wrong-accusation E2E pass.
- Spoiler-leak suite still passes (results only after accusation).

## M15: Player progress, settings & account management
**Depends on:** M14
**Scope:** `/me/progress/`; Progress screen; Settings (text size, reduced motion, tips, password change); data export; account deletion with cascade.
**Acceptance criteria:**
- `progress.spec` passes.
- Account deletion test confirms all player data removed, content intact.
- Preferences apply app-wide (text scale and reduced motion verified in component tests).

## M16: *The Missing Masterpiece*, complete
**Depends on:** M14 (all mechanics exist), M15
**Scope:** finish all content to Standard targets (CASE_DESIGN §6.1); commission/source and credit images; complete walkthrough; staff preview review; playtest protocol (TESTING_PLAN §9); contextual first-time tips (D-18 default).
**Acceptance criteria:**
- Full content suite (TESTING_PLAN §6) passes for this case.
- `golden-path.spec` and `wrong-accusation.spec` pass on this case.
- Publish gate from the playtest protocol met; reviewer checks F7–F11 recorded.

## M17: Cases 2 and 3 (content-only milestone)
**Depends on:** M16
**Requires decision:** **D-05** (number of launch cases), **D-16** (tone), **D-18** (tutorial approach for the Introductory case).
**Scope:** design, write, validate, and playtest an Introductory case (different crime type; doubles as onboarding) and a Hard case (layered contradictions). **Rule: no application code changes.** If a case genuinely needs a new mechanic, it goes through the "Extending mechanics" process (ARCHITECTURE §8) as a separately scoped task, and the roadmap is updated.
**Acceptance criteria:**
- Both cases pass the content suite and publish gate.
- Git diff for this milestone touches only `content/` (plus docs), or every code change is justified via the extension process.

## M18: Polish, accessibility & performance
**Depends on:** M17
**Requires decision:** **D-08** (light theme), **D-13** (phone support level), confirm **D-12** (audio) remains out.
**Scope:** full WCAG 2.2 AA audit (keyboard, screen reader, contrast, zoom/reflow); responsive pass at all breakpoints; motion polish + reduced-motion verification; empty/error states review; performance budget checks (TESTING_PLAN §11); copy review against voice guidelines; cross-browser E2E.
**Acceptance criteria:**
- `a11y.spec` and `mobile.spec` pass on all three cases; manual screen-reader pass documented.
- Lighthouse targets met; action p95 < 150 ms; casefile < 200 KB.
- Zero open "serious" UX issues from playtests.

## M19: Deployment & launch readiness
**Depends on:** M18
**Requires decision:** **D-07** (host), **D-17** (email provider), **D-06** (confirm no payments in v1.0).
**Scope:** production Dockerfile (gunicorn + WhiteNoise serving built SPA); managed PostgreSQL; environment config & secrets; `check --deploy` clean; HTTPS; backups and a restore drill; Sentry (optional); content deploy procedure (`validate_case` → `import_case` in release step); privacy policy & terms pages; smoke tests against staging; launch checklist.
**Acceptance criteria:**
- Staging deployment passes the full E2E suite.
- Database restore from backup demonstrated once.
- Release procedure documented in README and executed end-to-end for a content-only update.
- **v1.0 released.**

---

## Post-1.0: optional enhancements (M20+)

Order to be decided against player feedback. Each is independent unless noted.

| Milestone | Feature | Depends on / decision |
|---|---|---|
| M20 | Hint system (tiered, authored; scoring impact) | D-04; content format already reserves `hints` |
| M21 | Light "daylight" theme | D-08 |
| M22 | Achievements & detective rank | M15 |
| M23 | Shareable spoiler-free result cards / leaderboards | D-09 |
| M24 | Guest play (if not done in M5) | D-01 |
| M25 | Audio evidence & ambient sound | D-12; new evidence kind (extension process) |
| M26 | Image hotspots | Extension process (new action + condition atom) |
| M27 | Case series / seasons; "coming soon" teasers | Content + small library UI change |
| M28 | Theory comparison view; board grouping/export | M12, M13 |
| M29 | In-browser authoring tool / invited authors | D-10 |
| M30 | Localisation | Strings externalised since M2 |
| M31 | LLM-assisted free-text questioning mapped to authored topics | D-11 |
| ongoing | New cases | Content pipeline only |

## Coverage check: Essential features → milestones

| PRODUCT_SPEC area | Milestone(s) |
|---|---|
| 5.1 Accounts | M5, M15 |
| 5.2 Library & briefing | M6, M8 |
| 5.3 Workspace (locations, evidence, notebook, search, feed) | M9, M12 |
| 5.4 People & interviews | M10 |
| 5.5 Contradictions | M7 (engine), M10 (UI) |
| 5.6 Timeline | M11 |
| 5.7 Evidence board | M12 |
| 5.8 Theories | M13 |
| 5.9 Accusation & results | M14 |
| 5.10 Player progress | M15 |
| 5.11 Hints | M20 (D-04) |
| 5.12 Content pipeline | M3, M4, M7 (preview) |
| 5.13 Presentation | M2, M18 |
| 5.14 Launch content | M16, M17 |
| Deployment | M19 |

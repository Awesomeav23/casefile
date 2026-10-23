# Casefile: Architecture

**Status:** Planning draft. Describes the intended architecture; nothing is built yet.
**Related:** [DATA_MODEL](DATA_MODEL.md) · [API_PLAN](API_PLAN.md) · [CASE_DESIGN](CASE_DESIGN.md) · [TESTING_PLAN](TESTING_PLAN.md)

Guiding constraint: **one developer must be able to build, understand, and operate this.** Prefer Django and Vue defaults, one deployable backend, one database, and no message queues, microservices, or caches until measurements justify them.

---

## 1. System overview

```
┌──────────────────────────┐        HTTPS, JSON, session cookie + CSRF
│  Vue 3 SPA (TypeScript)  │ ───────────────────────────────────────────┐
│  Vite build, static files│                                            │
└──────────────────────────┘                                            ▼
                                                    ┌───────────────────────────────┐
                                                    │ Django + DRF (gunicorn)       │
 content/cases/<slug>/*.yaml ──► manage.py          │  accounts │ content │ play    │
                                 validate_case       │  services: discovery engine,  │
                                 import_case ───────►│  actions, scoring, importer   │
                                                    └──────────────┬────────────────┘
                                                                   │ Django ORM
                                                                   ▼
                                                    ┌───────────────────────────────┐
                                                    │ PostgreSQL                    │
                                                    │  content tables (per case)    │
                                                    │  spoiler tables (isolated)    │
                                                    │  playthrough state & event log│
                                                    └───────────────────────────────┘
```

- **Single origin in production**: the built SPA and `/api/` are served from the same domain (Django + WhiteNoise for static assets, or a reverse proxy in front). This avoids CORS and allows simple cookie sessions.
- **In development**, the Vite dev server proxies `/api` and `/media` to `runserver`.

## 2. Key technical decisions

| Decision | Choice | Why | Rejected alternative |
|---|---|---|---|
| Auth | Django session auth + CSRF cookie | Same-origin SPA; built-in, secure, nothing to manage on the client | JWT (token storage, refresh logic, revocation; unnecessary here) |
| Game logic location | **Server-authoritative** | Prevents spoiler leaks and cheating; one source of truth for discovery and scoring | Client-side engine with full case JSON (leaks solution) |
| Case authoring | YAML files in the repo → validated → imported into PostgreSQL | Version-controlled, reviewable in diffs, no authoring UI needed in v1.0 | Admin-only authoring (hard to review, no diffs); JSON (harder to write by hand) |
| Unlock rules | Small declarative condition language stored as JSONB | Covers every planned case shape; can be analysed statically for solvability | Per-case Python hooks (needs code per case); general scripting (can't be analysed) |
| Player progress | Append-only **event log** + derived **discovery** rows | Event log gives history, statistics, and debugging; discovery rows make reads cheap | Recomputing from events on every read; storing a single JSON blob |
| Evidence board | Layout stored as one JSONB document per playthrough | Board is UI state, read and written whole; no queries over it | Normalised pins/links tables (more code, no benefit) |
| API types | drf-spectacular OpenAPI → `openapi-typescript` generated types | Frontend and backend contracts stay in sync | Hand-written duplicate types |
| Frontend state | Pinia stores + a thin typed `fetch` client | Standard Vue; enough for this app | Adding a query/caching library (revisit only if needed) |
| Background jobs | None in v1.0 | All operations are fast and synchronous. Email goes out synchronously or through the provider's API | Celery/Redis (operational overhead) |

## 3. Backend

### 3.1 Django apps

| App | Responsibility |
|---|---|
| `accounts` | User model (custom, email login), `PlayerProfile`, registration, login/logout, password reset, account deletion/export |
| `content` | Case content models (player-visible and spoiler), case YAML schema, **validator**, **importer**, media handling, staff preview |
| `play` | Playthroughs, the **discovery engine**, the action handlers, contradictions, board, notes, theories, accusation, **scoring**, results, progress statistics |

A custom user model is defined from the first migration (Django recommends it, and it's painful to add later).

### 3.2 Services (plain Python modules, no framework)

| Module | Responsibility |
|---|---|
| `content/schema.py` | Pydantic (or dataclass + manual checks) models for each YAML file; format versioning |
| `content/validator.py` | Reference, graph, solvability, and fairness checks (CASE_DESIGN §6.6, §8). Pure functions over parsed content; no database needed |
| `content/importer.py` | Transactionally upserts a validated case into the database by stable keys; hashes and copies assets; enforces the update policy (§8) |
| `play/conditions.py` | Evaluates a `requires` expression against a set of facts. Pure function |
| `play/engine.py` | **Pure core** (built in M3): given parsed case content and a set of facts, returns the discovered set. The validator's simulation uses it directly. **Persistence wrapper** (built in M7): loads `Fact` rows, calls the core, and writes new `Discovery` rows |
| `play/actions.py` | One handler per action type (`visit_location`, `examine_evidence`, `ask_topic`, `present_evidence`, `flag_contradiction`). Each validates the action is allowed, records a `PlaythroughEvent`, calls the engine, and returns the delta |
| `play/visibility.py` | Builds the player's casefile from discovered items only. **The only path by which content reaches player serializers** |
| `play/scoring.py` | Scores an accusation against the answer key; computes outcome tier |
| `play/results.py` | Assembles the results payload (solution, red herrings, missed key evidence, statistics); only callable for accused playthroughs |

Views stay thin: authenticate → load playthrough (owner-scoped) → call service → serialize.

### 3.3 Action processing (data flow)

```
POST /api/v1/playthroughs/{id}/actions/  { "type": "present_evidence", "person": "daniel-reyes", "evidence": "camera-gap" }
  │
  ├─ 1. Auth + ownership check (404 if not the owner's playthrough)
  ├─ 2. Status check (must be in_progress, else 409)
  ├─ 3. Precondition check (person and evidence discovered, else 422; never reveal why beyond "not available")
  ├─ 4. BEGIN TRANSACTION (SELECT … FOR UPDATE on the playthrough row: serialises concurrent tabs)
  │     ├─ insert PlaythroughEvent (fact)
  │     ├─ engine.discover(playthrough) → new Discovery rows
  │     └─ update playthrough.last_active_at
  │   COMMIT
  └─ 5. Response: { action, repeat, result, discovered: { <type>: [<new items, fully serialized>] } }   (API_PLAN §4.1)
```

- **Idempotent**: repeating an action produces no new facts or discoveries. The same result is returned with `"repeat": true`.
- **Engine cost**: re-evaluating every condition after each action is O(items in case), a few hundred at most, so it's trivially fast. No incremental-dependency optimisation is needed.

### 3.4 Spoiler isolation

1. Spoiler content lives in **separate tables** (`CaseSolution`, `AnswerKey`, `RedHerring`, `Contradiction`). Player-facing serializers never import those models, except the contradiction explanation, which is serialized only through a found-contradiction discovery.
2. All player content goes through `play/visibility.py`, which reads only discovered keys.
3. `results` endpoints check `playthrough.status == accused`.
4. Media for non-starting content uses content-hashed filenames, so URLs can't be guessed from keys.
5. Automated leak tests verify all of this (TESTING_PLAN §5).

Known limitation: a determined player who inspects their own network traffic sees only what they've already discovered, which is acceptable.

## 4. Frontend

### 4.1 Structure

```
frontend/src/
├── api/            # client.ts (fetch wrapper, CSRF, error mapping), endpoints/*.ts, generated schema types
├── stores/         # Pinia: auth, library, playthrough, board, notes, theories, accusation, progress, ui
├── router/         # routes, guards (auth, playthrough ownership via API 404)
├── views/          # one per route (Landing, Library, Briefing, Workspace/*, Results, Progress, Auth, Settings)
├── components/
│   ├── ui/         # design-system primitives: Button, Card, Dialog, Tabs, Badge, Toast, Tooltip, EmptyState…
│   ├── casefile/   # EvidenceCard, EvidenceViewer, PersonCard, StatementQuote, RecordView, DiscoveryToast…
│   ├── interview/  # TopicList, ConversationLog, PresentEvidencePicker
│   ├── timeline/   # TimelineLanes, TimelineEvent, TimelineList (mobile)
│   ├── board/      # BoardCanvas, BoardCard, BoardLink, BoardKeyboardControls, BoardList (mobile)
│   └── accusation/ # QuestionStep, CitationPicker, ReviewSummary
├── composables/    # useAction, useNewBadges, useKeyboardShortcuts, useReducedMotion…
└── styles/         # tokens.css, base.css, themes
```

### 4.2 State and data flow

- `playthroughStore` holds the **casefile**: all discovered people, locations, evidence, topics, statements, events, contradictions, and facts. It's loaded once via `GET /playthroughs/{id}/casefile/` when the workspace opens.
- **Search** (command palette) runs client-side over the casefile store, so no search endpoint is needed. The data is small and already scoped to discovered content.
- Actions call `POST …/actions/`. The response's `discovered` delta is **merged** into the store, and a discovery toast is shown. Actions are **not optimistic**: the server decides what's revealed.
- Board, notes, and theories are player-authored. They save with **optimistic updates** and debounced writes (board: 1 s debounce; notes: on blur and every 3 s while typing). They use a `version` field to detect conflicts between tabs (409 → reload prompt).
- "New" badges: the client records `last_viewed_at` per item in the store and syncs it via `POST …/seen/` (batched), so badges survive across devices.

### 4.3 Routing (summary; full map in SCREEN_DESIGN)

`/`, `/cases`, `/cases/:slug`, `/play/:playthroughId/{overview|locations|evidence|people|timeline|board|theories|accuse}`, `/play/:playthroughId/results`, `/progress`, `/login`, `/register`, `/reset-password`, `/settings`.

Route guards: workspace routes require auth (D-01) and redirect to results if the playthrough is already accused.

### 4.4 Evidence board implementation

Spike in milestone M10: evaluate **Vue Flow** (`@vue-flow/core`) against a custom SVG/pointer-events canvas. Selection criteria: keyboard operability, performance with 100 cards, bundle size, and the ability to style cards as case-file items. Whichever wins, keyboard and list alternatives are mandatory (UI_UX_GUIDELINES §9).

## 5. Authentication and authorization

- Email + password via Django auth; Argon2 password hashing; login rate-limited (DRF throttling, per-IP and per-account).
- `GET /api/v1/auth/csrf/` sets the CSRF cookie; the client sends `X-CSRFToken` on unsafe methods.
- Session cookie: `HttpOnly`, `Secure` (prod), `SameSite=Lax`.
- Permissions:
  - Public: landing data, case library, case briefings (published cases only).
  - Authenticated: start and play playthroughs, progress, profile.
  - Owner-only: every `/playthroughs/{id}/…` route. Non-owners get **404** (not 403), so playthrough IDs can't be probed.
  - Staff: draft case preview, Django admin.
- Guest play (D-01): if approved, the planned approach is an anonymous Django session that owns a playthrough with `user = NULL` plus `guest_session_key`, claimed on sign-up. The data model allows for this (DATA_MODEL §5, `play_playthrough`).

## 6. Error handling

**API error envelope (all non-2xx):**
```json
{ "error": { "code": "playthrough_not_in_progress", "message": "This investigation is closed.", "details": {} } }
```

| Status | Used for |
|---|---|
| 400 | Malformed request / serializer validation (`details` holds field errors) |
| 401 | Not authenticated |
| 403 | CSRF failure (`csrf_failed`) or a staff-only endpoint called by a non-staff user (`permission_denied`) |
| 404 | Not found **or** not owned |
| 409 | State conflict: playthrough not in progress, stale `version` on board/notes/theories, accusation already submitted, case not available |
| 422 | **Investigation action** not available (it references an undiscovered item): `action_unavailable` |

Undiscovered references follow one rule. In an investigation **action** they return 422 `action_unavailable`. In **player-authored payloads** (board, notes, theories, accusation citations) they return 400 `invalid_reference`.
| 429 | Rate limited |
| 500 | Unexpected; generic message, details logged server-side |

This will be implemented with a custom DRF exception handler (M1). Error `code`s are a documented, stable enum (API_PLAN §9).

**Frontend:** the API client turns errors into a typed `ApiError`. Field errors appear inline. 409s on authored content offer "Reload latest". Network failures show a non-blocking toast with retry. Failed actions leave the UI unchanged. Unknown routes and unowned playthroughs show a 404 screen. A global error boundary view catches render errors.

**Logging/monitoring:** structured logging to stdout. Optional Sentry (frontend + backend) in the deployment milestone.

## 7. Media and static assets

- Case assets are copied on import to `MEDIA_ROOT/cases/<slug>/<sha256-prefix>.webp`. The DB stores the hashed path.
- Served by WhiteNoise/reverse proxy in v1.0. Object storage (S3-compatible) is a drop-in later via `django-storages` if hosting requires it (D-07).
- The SPA build is served as static files with long-lived caching for hashed bundles.

## 8. Supporting additional mysteries

**Adding a case = adding a content folder.** The engine supports any case built from the fixed mechanics: locations, evidence, topics, reactions, timeline, contradictions, and configurable accusation questions. That covers theft, murder, disappearance, fraud, and similar formats without code changes.

**Case updates (default pending D-14):**
- The importer upserts by `(case, type, key)`.
- **Additive changes** (new items, edited text, new conditions that only add paths) apply immediately, even to in-progress playthroughs. The engine re-evaluates on the next action.
- **Breaking changes** (removed keys, changed answer key, changed accusation questions) are **refused** while any playthrough of that case is `in_progress`, unless run with `--force`. `--force` bumps `content_version` and marks affected playthroughs `stale`, and the UI offers a restart.
- Every playthrough records the `content_version` it started on, so its results stay interpretable.

**Extending mechanics.** Occasionally a case needs a genuinely new mechanic (e.g. a combination lock, audio evidence). The extension points are:
1. a new condition atom in `conditions.py` + validator simulation,
2. a new action handler in `actions.py`,
3. a new evidence `kind` renderer in the frontend.

Each requires a format-version bump and tests. This is the **only** case where new content requires code.

**LLM interviews (D-11):** if ever pursued, they would plug in as an alternative `ask` handler that maps free text to an existing topic. Authored statements would remain the source of truth, so solvability guarantees hold.

## 9. Environments & configuration

| Env | Notes |
|---|---|
| Local | Docker Compose PostgreSQL (optional), `runserver`, Vite dev server |
| CI | GitHub Actions: PostgreSQL service container; runs lint, type-check, unit/integration tests, `validate_case` on all cases, Playwright |
| Production | Single container (gunicorn + WhiteNoise serving the built SPA) + managed PostgreSQL. Host: D-07 |

Configuration comes from environment variables (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `EMAIL_*`, `SENTRY_DSN`) via `django-environ` or equivalent. Secrets are never committed.

## 10. Performance & scale expectations

- Target: hundreds of concurrent players, not millions. A single small instance should suffice.
- Casefile payload: < 200 KB JSON for a Hard case fully discovered.
- Action round-trip: < 150 ms server time at p95.
- Indexes are defined in DATA_MODEL. No cache layer is planned until profiling shows a need.

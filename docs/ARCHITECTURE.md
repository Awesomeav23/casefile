# Casefile: Architecture

**Status:** Planning draft. Describes the intended architecture; nothing is built yet.
**Related:** [DATA_MODEL](DATA_MODEL.md) · [API_PLAN](API_PLAN.md) · [CASE_DESIGN](CASE_DESIGN.md) · [TESTING_PLAN](TESTING_PLAN.md) · decisions in [PRODUCT_SPEC §9](PRODUCT_SPEC.md#9-decisions)

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
                                 validate_case       │  services: player identity,   │
                                 import_case ───────►│  discovery engine, actions,   │
                                                    │  flags, hints, scoring        │
                                                    └──────────────┬────────────────┘
                                                                   │ Django ORM
                                                                   ▼
                                                    ┌───────────────────────────────┐
                                                    │ PostgreSQL                    │
                                                    │  content tables (per case)    │
                                                    │  spoiler tables (isolated)    │
                                                    │  playthrough state & event log│
                                                    └───────────────────────────────┘
        Planned hosting (D-07): Render. One Web Service runs Django and serves the built SPA;
        Render PostgreSQL provides the database (topology default pending D-26; see §9).
```

- **Single origin in production**: the built SPA and `/api/` are served from the same origin (Django + WhiteNoise serving the Vue build). This avoids CORS and keeps cookie sessions and CSRF simple, for guests and account holders alike.
- **In development**, the Vite dev server (port 5180) proxies `/api`, `/admin`, and `/static` to `runserver` (port 8010).

## 2. Key technical decisions

| Decision | Choice | Why | Rejected alternative |
|---|---|---|---|
| Auth | Django session auth + CSRF cookie | Same-origin SPA; built-in, secure, nothing to manage on the client | JWT (token storage, refresh logic, revocation; unnecessary here) |
| **Guest play (D-01)** | A **guest identity** (random UUID) stored in the Django session of an anonymous visitor. Playthroughs are owned by *either* a user *or* a guest ID | Reuses the session/CSRF machinery; no separate token system. Survives login (Django keeps session data when an anonymous session logs in), so claiming is simple | Client-only local storage progress (no server authority, leaks spoilers); forcing sign-up (rejected by D-01) |
| Game logic location | **Server-authoritative** | Prevents spoiler leaks and cheating; one source of truth for discovery and scoring | Client-side engine with full case JSON (leaks solution) |
| Case authoring | YAML files in the repo → validated → imported into PostgreSQL | Version-controlled, reviewable in diffs, no authoring UI needed in v1.0 | Admin-only authoring (hard to review, no diffs); JSON (harder to write by hand) |
| Unlock rules | Small declarative condition language stored as JSONB, also used for hint relevance | Covers every planned case shape; can be analysed statically for solvability and hint coverage | Per-case Python hooks (needs code per case); general scripting (can't be analysed) |
| Player progress | Append-only **event log** + derived **discovery** rows | Event log gives history, statistics, and debugging; discovery rows make reads cheap | Recomputing from events on every read; storing a single JSON blob |
| **Contradiction flags (D-03)** | Player flags are rows the player owns. Each is verified when created or revised; confirmed flags create a permanent `contradiction` fact | Satisfies "revise or remove" without breaking monotonic unlocks | Flags as one-shot actions (can't be revised); un-confirming contradictions (would break no-dead-ends) |
| **Hints (D-04)** | Authored hint tracks in spoiler tables; the server decides which track is relevant from the player's facts and reveals one tier per request | Hints stay content, not code; no hint text reaches the client unrequested | Client-side hint logic (leaks spoilers); generic auto-hints (can't guarantee they don't give answers away) |
| Evidence board | Layout stored as one JSONB document per playthrough | Board is UI state, read and written whole; no queries over it | Normalised pins/links tables (more code, no benefit) |
| API types | drf-spectacular OpenAPI → `openapi-typescript` generated types | Frontend and backend contracts stay in sync | Hand-written duplicate types |
| Frontend state | Pinia stores + a thin typed `fetch` client | Standard Vue; enough for this app | Adding a query/caching library (revisit only if needed) |
| Background work | No queue. One **scheduled management command** (`purge_guest_data`, D-22) run by a Render Cron Job (verify availability and cost before M20) | All request work is fast and synchronous | Celery/Redis (operational overhead) |
| **Hosting (D-07)** | Render: Web Service (Django + built SPA) + Render PostgreSQL, described in a `render.yaml` Blueprint | One platform for all three parts; same-origin cookies; infrastructure in the repo | Split Static Site + API on different `*.onrender.com` hosts (cross-site cookies; see §9 and D-26) |
| **Case assets on Render** | Built into the deploy artifact from the repo at **build time** (hashed, collected as static files), not written to disk at import time | Render service filesystems are ephemeral unless a persistent disk is attached (verify), and assets already live in git | Media uploads to local disk (lost on redeploy); object storage (extra service; only if assets outgrow the repo) |

## 3. Backend

### 3.1 Django apps

| App | Responsibility |
|---|---|
| `accounts` | User model (custom, email login), `PlayerProfile`, registration, login/logout, password change/reset, account deletion/export, **guest identity and claim-on-login** |
| `content` | Case content models (player-visible and spoiler, incl. hint tracks), case YAML schema, **validator**, **importer**, asset hashing, staff preview |
| `play` | Playthroughs, the **discovery engine**, action handlers, **contradiction flags**, **hints**, board, notes, theories, accusation, **scoring**, results, progress statistics |

A custom user model is defined from the first migration (Django recommends it, and it's painful to add later).

### 3.2 Services (plain Python modules, no framework)

| Module | Responsibility |
|---|---|
| `accounts/identity.py` | `get_player(request)` returns a `Player` (either `user` or `guest_id`). It creates a guest ID lazily on the first write, never on read-only browsing. Every playthrough query is scoped through it |
| `accounts/claim.py` | On register/login, reassigns the session's guest playthroughs to the user in one transaction, applying the D-23 conflict rule, then clears the guest ID |
| `content/schema.py` | Pydantic (or dataclass + manual checks) models for each YAML file; format versioning |
| `content/validator.py` | Reference, graph, solvability, hint, and fairness checks (CASE_DESIGN §6.7, §8). Pure functions over parsed content; no database needed |
| `content/assets.py` | Deterministically hashes case assets (`sha256` of file bytes) and copies them to the static source dir at **build time** (`manage.py collect_case_assets`) |
| `content/importer.py` | Transactionally upserts a validated case into the database by stable keys; stores hashed asset paths computed by `assets.py` (same function, so paths match); enforces the update policy (§8) |
| `play/conditions.py` | Evaluates a `requires` expression against a set of facts. Pure function |
| `play/engine.py` | **Pure core** (built in M3): given parsed case content and a set of facts, returns the discovered set. The validator's simulation uses it directly. **Persistence wrapper** (built in M7): loads `Fact` rows, calls the core, and writes new `Discovery` rows |
| `play/actions.py` | One handler per investigation action (`visit_location`, `examine_evidence`, `ask_topic`, `present_evidence`). Each validates the action is allowed, records a `PlaythroughEvent`, calls the engine, and returns the delta |
| `play/flags.py` | Create / revise / remove contradiction flags. Verifies a pairing against authored contradictions (incl. `accept_also`, either order). On a match: marks the flag confirmed, adds the `contradiction` fact, runs the engine. No penalty bookkeeping (D-03) |
| `play/hints.py` | Computes offered hint tracks (`requires` met, `resolved_when` not met) from facts; reveals the next tier on request; records `HintReveal` rows |
| `play/visibility.py` | Builds the player's casefile from discovered items only. **The only path by which content reaches player serializers** |
| `play/scoring.py` | Scores an accusation against the answer key; computes outcome tier (hint use doesn't affect it unless D-21 decides otherwise) |
| `play/results.py` | Assembles the results payload (solution, red herrings, missed key evidence, statistics incl. hints used); only callable for accused playthroughs |

Views stay thin: resolve player → load playthrough (player-scoped) → call service → serialize.

### 3.3 Action processing (data flow)

```
POST /api/v1/playthroughs/{id}/actions/  { "type": "present_evidence", "person": "daniel-reyes", "evidence": "camera-gap" }
  │
  ├─ 1. Resolve player (user or guest) + ownership check (404 if not this player's playthrough)
  ├─ 2. Status check (must be in_progress, else 409)
  ├─ 3. Precondition check (person and evidence discovered, else 422; never reveal why beyond "not available")
  ├─ 4. BEGIN TRANSACTION (SELECT … FOR UPDATE on the playthrough row: serialises concurrent tabs)
  │     ├─ insert PlaythroughEvent (+ Fact if new)
  │     ├─ engine.discover(playthrough) → new Discovery rows
  │     └─ update playthrough.last_active_at
  │   COMMIT
  └─ 5. Response: { action, repeat, result, discovered: { <type>: [<new items, fully serialized>] } }   (API_PLAN §4.1)
```

- **Idempotent**: repeating an action produces no new facts or discoveries. The same result is returned with `"repeat": true`.
- **Flags** (`POST/PATCH/DELETE …/flags/`) use the same steps 1–4. A confirmed flag returns the same `discovered` delta shape.
- **Engine cost**: re-evaluating every condition after each action is O(items in case), a few hundred at most, so it's trivially fast. No incremental-dependency optimisation is needed.

### 3.4 Spoiler isolation

1. Spoiler content lives in **separate tables** (`CaseSolution`, `AnswerKey`, `RedHerring`, `Contradiction`, `HintTrack`, `Hint`). Player-facing serializers never import those models, with two narrow exceptions: a contradiction explanation is serialized only through a confirmed flag, and a hint tier's text only through a `HintReveal` row.
2. All player content goes through `play/visibility.py` (and `play/hints.py` for revealed hints), which read only discovered or revealed keys.
3. `results` endpoints check `playthrough.status == accused`.
4. Asset URLs are content-hashed, so URLs can't be guessed from keys.
5. Automated leak tests verify all of this (TESTING_PLAN §5).

Known limitations:
- A determined player who inspects their own network traffic sees only what they've already discovered, which is acceptable.
- Because the repository is public (D-19), anyone can read the YAML solutions on GitHub. This is accepted for now (D-25). Server-side isolation still protects the *game* from accidental spoilers.

## 4. Frontend

### 4.1 Structure

```
frontend/src/
├── api/            # client.ts (fetch wrapper, CSRF, error mapping), endpoints/*.ts, generated schema types
├── stores/         # Pinia: auth (user | guest), library, playthrough (incl. flags), hints, board, notes, theories, accusation, progress, ui
├── router/         # routes, guards (playthrough ownership via API 404)
├── views/          # one per route (Landing, Library, Briefing, Workspace/*, Results, Progress, Auth, Settings)
├── components/
│   ├── ui/         # design-system primitives (M2): UiButton, UiIconButton, UiCard, UiDialog (+sheet), UiTabs, UiBadge, UiToastRegion, UiSkeleton, UiEmptyState
│   ├── casefile/   # EvidenceCard, EvidenceViewer, PersonCard, StatementQuote, RecordView, DiscoveryToast…
│   ├── interview/  # TopicList, ConversationLog, PresentEvidencePicker
│   ├── contradictions/ # FlagDialog, MyFlagsList, ConfirmedContradictionCard
│   ├── hints/      # HintButton, HintPanel, HintTierCard
│   ├── timeline/   # TimelineLanes, TimelineEvent, TimelineList (mobile)
│   ├── board/      # BoardCanvas, BoardCard, BoardLink, BoardKeyboardControls, BoardList (mobile)
│   ├── accusation/ # InvestigationReview, QuestionStep, CitationPicker, ReviewSummary
│   └── account/    # GuestBanner, SaveProgressPrompt, ClaimResultNotice
├── composables/    # useAction, useNewBadges, useKeyboardShortcuts, useReducedMotion…
├── i18n/           # externalised UI strings: en.ts, exposed as `m` (M2)
├── test/           # Vitest setup + axe helper (src/test/a11y.ts)
└── styles/         # tokens.css, base.css, themes
```

### 4.2 State and data flow

- `playthroughStore` holds the **casefile**: all discovered people, locations, evidence, topics, statements, events, confirmed contradictions, the player's flags, and facts. It's loaded once via `GET /playthroughs/{id}/casefile/` when the workspace opens.
- **Search** (command palette) runs client-side over the casefile store, so no search endpoint is needed. The data is small and already scoped to discovered content.
- Actions and flag submissions are **not optimistic**: the server decides what's revealed. The response's `discovered` delta is **merged** into the store, and a discovery toast is shown.
- `hintsStore` fetches `GET …/hints/` lazily when the hint panel opens, and again after each discovery. It shows only revealed tiers plus whether another tier or track is available.
- Board, notes, and theories are player-authored. They save with **optimistic updates** and debounced writes (board: 1 s debounce; notes: on blur and every 3 s while typing). They use a `version` field to detect conflicts between tabs (409 → reload prompt).
- "New" badges: `POST …/seen/` (batched) records seen items server-side, so badges survive across devices for account holders and across reloads for guests.
- `authStore` knows whether the visitor is a user, a guest with progress, or a fresh visitor (`GET /auth/me/`). After login/register it shows the claim result (API_PLAN §2) and refreshes library/progress.
- Guest preferences (text size, reduced motion) live in `localStorage`. Account preferences live in the profile and override them after login.

### 4.3 Routing (summary; full map in SCREEN_DESIGN)

`/`, `/cases`, `/cases/:slug`, `/play/:playthroughId/{overview|locations|evidence|people|timeline|board|theories|accuse}`, `/play/:playthroughId/results`, `/progress`, `/login`, `/register`, `/reset-password`, `/settings`.

Route guards: **no route except `/settings` (account section) requires an account** (D-01). Workspace routes redirect to results if the playthrough is already accused. A playthrough the current player doesn't own shows the 404 screen.

### 4.4 Evidence board implementation

Spike in milestone M10: evaluate **Vue Flow** (`@vue-flow/core`) against a custom SVG/pointer-events canvas. Selection criteria: keyboard operability, performance with 100 cards, bundle size, and the ability to style cards as case-file items. Whichever wins, keyboard and list alternatives are mandatory (UI_UX_GUIDELINES §9).

## 5. Identity, authentication, and authorization

**Player identity (D-01).** Every request resolves to one of:

| Identity | How | Owns playthroughs via |
|---|---|---|
| Account holder | Django session with authenticated user | `playthrough.user_id` |
| Guest | Anonymous Django session containing `guest_id` (UUID4) | `playthrough.guest_id` |
| Visitor | No session yet (read-only browsing) | — |

- A guest ID is created **lazily** when a visitor first starts a playthrough. Browsing the library or briefings creates nothing.
- The guest session cookie lasts for the D-22 retention period (default 90 days), renewed on activity. The account session uses Django's default age unless "remember me" is added later.
- **Claim on login/register:** `claim.py` runs immediately after `login()`. Django preserves the anonymous session's data when a user logs in, so `guest_id` is still available. All of that guest's playthroughs, events, flags, hints, notes, board, theories, and accusations move to the user in one transaction. D-23 resolves conflicts with an existing in-progress playthrough of the same case. The response lists what was claimed.
- **Logout** ends the session. A guest who later starts again on the same browser gets a new guest ID, because claimed progress now belongs to the account.
- **Guest abuse limits:** per-IP throttle on starting playthroughs (API_PLAN §10). Guest rows are purged by `purge_guest_data` after D-22's inactivity period.

**Authentication details**
- Email + password via Django auth; Argon2 password hashing; login rate-limited (DRF throttling, per-IP and per-account).
- `GET /api/v1/auth/csrf/` sets the CSRF cookie; the client sends `X-CSRFToken` on unsafe methods (guests included).
- Session cookie: `HttpOnly`, `Secure` (prod), `SameSite=Lax`.

**Permissions**
- **Public:** landing data, case library, case briefings (published cases only).
- **Player** (account holder *or* guest): start and play playthroughs, flags, hints, board/notes/theories, accusation, results, progress.
- **Account:** profile, password change, data export, account deletion.
- **Owner-only:** every `/playthroughs/{id}/…` route is scoped to the requesting player. Other players (account or guest) get **404**, not 403, so playthrough IDs can't be probed.
- **Staff:** draft case preview, Django admin.

## 6. Error handling

**API error envelope (all non-2xx):**
```json
{ "error": { "code": "playthrough_not_in_progress", "message": "This investigation is closed.", "details": {} } }
```

| Status | Used for |
|---|---|
| 400 | `validation_error` (`details` holds field errors), `malformed_request` (unparseable body), `invalid_reference` |
| 401 | Not authenticated (account-only endpoints) |
| 403 | CSRF failure (`csrf_failed`) or a staff-only endpoint called by a non-staff user (`permission_denied`) |
| 404 | Not found **or** not owned by this player; also any unknown `/api/` route |
| 405 / 406 / 415 | `method_not_allowed` / `not_acceptable` / `unsupported_media_type` (JSON only) |
| 409 | State conflict: playthrough not in progress, stale `version` on board/notes/theories, accusation already submitted, results unavailable, case not available, confirmed flag can't be changed |
| 422 | **Investigation action** not available (it references an undiscovered item): `action_unavailable` |
| 429 | Rate limited (`Retry-After` header + `details.retry_after_seconds`) |
| 500 | Unexpected; generic message, details logged server-side |
| 503 | `service_unavailable`: health check when the database is unreachable |

Undiscovered references follow one rule. In an investigation **action** or **flag** they return 422 `action_unavailable`. In **player-authored payloads** (board, notes, theories, accusation citations) they return 400 `invalid_reference`.

Implemented in M1 as a custom DRF exception handler (`casefile/api/exceptions.py`), plus a catch-all JSON 404 for unknown `/api/` routes and a JSON `handler500` for `/api/` paths. Error `code`s are a documented, stable enum (API_PLAN §9).

**Frontend:** the API client turns errors into a typed `ApiError`. Field errors appear inline. 409s on authored content offer "Reload latest". Network failures show a non-blocking toast with retry. Failed actions leave the UI unchanged. Unknown routes and unowned playthroughs show a 404 screen. A global error boundary view catches render errors.

**Logging/monitoring:** structured logging to stdout (collected by Render's log stream). Optional Sentry (frontend + backend) in the deployment milestone.

## 7. Static files and case assets

- **Build time** (`manage.py collect_case_assets`): every case's `assets/` files are copied to `static_src/cases/<slug>/<sha256-prefix>.<ext>`, then `collectstatic` + WhiteNoise serve them with long-lived caching. Hashing is deterministic, so the importer computes the same paths without touching the filesystem.
- **Import time** (`import_case`): writes database rows only, including the hashed asset paths. Safe to run in a separate release step.
- The SPA build (`frontend/dist`) is also collected as static files and served by WhiteNoise with an `index.html` fallback for client-side routes.
- If assets ever outgrow the repository, switch to S3-compatible object storage via `django-storages`. The asset path abstraction in `assets.py` keeps that change contained.

## 8. Supporting additional mysteries

**Adding a case = adding a content folder** (D-05). The engine supports any case built from the fixed mechanics: locations, evidence, topics, reactions, timeline, contradictions, **hint tracks**, and configurable accusation questions. That covers theft, murder, disappearance, fraud, and similar formats without code changes. Launch requires three such cases, and each one must ship with no application code changes (roadmap M17–M18 acceptance criteria).

**Case updates (default pending D-14):**
- The importer upserts by `(case, type, key)`.
- **Additive changes** (new items, edited text, new hint tracks, new conditions that only add paths) apply immediately, even to in-progress playthroughs. The engine re-evaluates on the next action.
- **Breaking changes** (removed keys, changed answer key, changed accusation questions) are **refused** while any playthrough of that case is `in_progress`, unless run with `--force`. `--force` bumps `content_version` and marks affected playthroughs `stale`, and the UI offers a restart.
- Every playthrough records the `content_version` it started on, so its results stay interpretable.

**Extending mechanics.** Occasionally a case needs a genuinely new mechanic (e.g. a combination lock, audio evidence). The extension points are:
1. a new condition atom in `conditions.py` + validator simulation,
2. a new action handler in `actions.py`,
3. a new evidence `kind` renderer in the frontend.

Each requires a format-version bump and tests. This is the **only** case where new content requires code.

**LLM interviews (D-11):** if ever pursued, they would plug in as an alternative `ask` handler that maps free text to an existing topic. Authored statements would remain the source of truth, so solvability guarantees hold.

## 9. Environments, repository, and deployment

### 9.1 Environments

| Env | Notes |
|---|---|
| Local | Docker Compose PostgreSQL 16 on port 5436, `runserver 8010`, Vite dev server on 5180 (proxies `/api`, `/admin`, `/static`) |
| CI | GitHub Actions: PostgreSQL service container; lint, type-check, unit/integration tests, `validate_case` on all cases, Playwright. Active only once the public repo exists (D-19, D-28) |
| Staging / Production | Render (D-07); topology below. Whether a separate staging service is affordable is part of the pre-deployment verification |

Configuration comes from environment variables (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `EMAIL_*`, `SENTRY_DSN`) via `django-environ` or equivalent. Secrets are never committed. On Render they're set as environment variables or secret files (§9.3).

### 9.2 Public repository rules (D-19)

- The repository is public on GitHub. Development happens locally first, and the first push happens only when the owner asks (D-28).
- **Never committed:** `.env`, credentials, database dumps, `node_modules`, build output (`frontend/dist`, `staticfiles`), coverage reports, Playwright artifacts. `.gitignore` covers these, and the `detect-private-key` hook runs on every commit.
- `.env.example` contains **placeholder values only**, which are usable for the local Docker database and never valid anywhere else.
- Before the first push: run a secret scan over the full history (e.g. `gitleaks`), confirm no real credentials, and confirm the README spoiler notice (D-25).
- **CI before trust:** the workflow is configured before code milestones rely on it. Branch protection ("require CI to pass") is switched on only after the first green run on GitHub.

### 9.3 Render deployment (D-07; topology default pending D-26)

**Default topology:** one Render **Web Service** plus one Render **PostgreSQL** database, declared in `render.yaml` (Blueprint).

| Step | Command (planned) |
|---|---|
| Build | `pip install -r backend/requirements.txt && npm ci --prefix frontend && npm run build --prefix frontend && python backend/manage.py collect_case_assets && python backend/manage.py collectstatic --noinput` |
| Release / pre-deploy | `python backend/manage.py migrate && python backend/manage.py import_case --all` |
| Start | `gunicorn casefile.wsgi --chdir backend` |
| Scheduled | `python backend/manage.py purge_guest_data` (daily), as a Render Cron Job |

**Alternative (D-26):** Render **Static Site** for the Vue build plus a Web Service for the API. This only works cleanly if both sit under one custom domain (e.g. `casefile.example` and `api.casefile.example`), which makes them same-site for cookies; then add CORS with credentials and `CSRF_TRUSTED_ORIGINS`. Separate `*.onrender.com` subdomains are likely treated as different sites by browsers, which would break `SameSite=Lax` session cookies for guests and accounts. Verify this before choosing.

**Must verify before deployment (M20)**. Nothing here is assumed:
- current pricing and free-tier limits for Web Services, PostgreSQL, and Cron Jobs (including any database expiry or sleep-on-idle behaviour);
- whether a pre-deploy/release command is available on the chosen instance type (if not, run `migrate`/`import_case` at the start of the start command, guarded by a lock);
- the supported Python and Node versions in Render's build environment (pinned: Python 3.13, Node 24 LTS);
- PostgreSQL major-version availability (pinned locally: 16);
- backup and point-in-time-restore options for the chosen database plan;
- custom domain + managed TLS setup; region availability;
- filesystem persistence (expected to be ephemeral, which is why assets are built in, §7);
- outbound email: Render doesn't send email itself, so pick a provider (D-17).

## 10. Performance & scale expectations

- Target: hundreds of concurrent players, not millions. A single small instance should suffice.
- Casefile payload: < 200 KB JSON for a Hard case fully discovered.
- Action and flag round-trip: < 150 ms server time at p95.
- Guest data growth is bounded by the D-22 purge and the per-IP start throttle.
- Indexes are defined in DATA_MODEL. No cache layer is planned until profiling shows a need.

# Casefile

> An immersive mystery investigation platform. Read the briefing, walk the scene, question suspects, catch the lie, and name the culprit, with proof.

**Status: M0–M3 complete.** This repository contains the design documentation, development tooling (local PostgreSQL, lint hooks, CI), licensing, the Django backend foundation (custom user model, error envelope, health and schema endpoints), the Vue frontend foundation (design tokens, accessible UI primitives, placeholder routes for every screen, typed API client), and the case format with its validator (`validate_case`). No application code exists yet. Every feature described below is *planned*, not implemented. See [the roadmap](docs/DEVELOPMENT_ROADMAP.md) for what comes next.

---

## Vision

Most "mystery games" on the web are quizzes wearing a trench coat: read a story, pick a name. Casefile aims to feel like a real investigation:

- You **gather** evidence by examining locations and documents. You do not get it handed to you.
- You **question** suspects topic by topic and **confront** them with evidence.
- You **catch contradictions** between what people say and what the evidence shows, and each one you catch opens new lines of inquiry.
- You **reconstruct the timeline** and **build theories** on an evidence board.
- You **submit a reasoned accusation** naming who, how, and why, backed by the evidence you choose. You are scored on the reasoning, not just the name.

Every case is **content, not code**. A new mystery is a folder of YAML files and images that is validated (including an automated solvability check) and imported into the database.

## Planned features

Essential (v1.0) and optional features are listed in full in [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md). In brief:

| Area | Planned capability |
|---|---|
| Case library | Browse published cases with difficulty, length, and your status on each |
| Briefing | Case introduction, objective, and starting persons of interest |
| Investigation workspace | Locations, evidence examination, interviews, and a case notebook |
| Interviews | Topic-based questioning, presenting evidence to suspects, recorded statements |
| Guest play | Play any case with no account; optionally create one to keep progress across devices (guest progress is carried over) |
| Contradictions | Pair a statement with conflicting evidence to break an alibi and unlock new leads. No penalty for wrong flags; revise or remove them |
| Timeline | Reconstructed events by person and location, claimed vs. verified |
| Evidence board | Pin, arrange, and connect items; attach notes |
| Theories | Draft and compare competing theories |
| Hints | Optional, three-tier hints that point you where to look, never at the answer |
| Accusation | Review your investigation, then make one structured, evidence-backed final accusation |
| Results | Scored outcome, full solution, and the evidence you missed. Replay any time |
| Player progress | Solved cases, ratings, in-progress investigations, statistics |
| Case pipeline | YAML authoring format, validator, solvability checker, importer |

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3.5 (Composition API, `<script setup>`), TypeScript 6, Vite 8, Vue Router 5, Pinia 4 |
| Backend | Python 3.13, Django 5.2 LTS, Django REST Framework 3.18 |
| Database | PostgreSQL |
| API schema | OpenAPI generated with drf-spectacular; TypeScript types generated from it |
| Testing | pytest + pytest-django (backend), Vitest + Vue Test Utils (frontend), Playwright (end-to-end) |
| CI | GitHub Actions: secret scan (gitleaks), lint, backend checks/tests against PostgreSQL 16, frontend lint/type-check/tests/build, API-type drift check |
| Hosting (planned) | Render: Web Service (Django + built Vue SPA) and Render PostgreSQL. Pricing and requirements to be verified before deployment |

Rationale is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Prerequisites

Pinned in M0:

| Tool | Version | Pinned in |
|---|---|---|
| Python | 3.13 | `.python-version` |
| Node.js | 24 LTS (with npm 11) | `.nvmrc` |
| PostgreSQL | 16 | `docker-compose.yml` (`postgres:16`) |
| Docker + Docker Compose | any recent | runs the local database |
| Git | any recent | |

Locally, PostgreSQL listens on **port 5436**, so it doesn't clash with other local projects on 5432–5435. Change `POSTGRES_PORT` in `.env` if needed.

## Planned repository layout

```
casefile/
├── README.md
├── docs/                    # Planning and design documentation (this phase)
├── backend/                 # Django project (planned)
│   ├── casefile/            #   settings, urls, wsgi/asgi
│   ├── accounts/            #   users and player profiles
│   ├── content/             #   case content models, importer, validator
│   └── play/                #   playthroughs, discovery engine, actions, theories, accusations
├── frontend/                # Vue 3 + TypeScript app
│   └── src/
├── content/
│   └── cases/               # One folder per mystery (YAML + assets)
│       └── the-missing-masterpiece/
└── e2e/                     # Playwright tests (planned)
```

## Setup

### Working now (M0 tooling + M1 backend foundation)

These commands were run and verified during M0 and M1:

```bash
# 1. Environment file
cp .env.example .env

# 2. Database (PostgreSQL 16 on localhost:5436)
docker compose up -d db
docker inspect -f '{{.State.Health.Status}}' casefile-db     # → healthy

# 3. Repo tooling (pre-commit hooks)
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pre-commit install
.venv/bin/pre-commit run --all-files

# 4. Backend (Django 5.2 LTS + DRF); reads the root .env
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8010             # http://localhost:8010
curl localhost:8010/api/v1/health/                    # → {"status":"ok","database":"ok"}
# OpenAPI schema: /api/v1/schema/   Interactive docs (DEBUG only): /api/v1/docs/
.venv/bin/python manage.py createsuperuser            # optional: Django admin at /admin/

# 5. Backend checks (the same ones CI runs)
.venv/bin/python manage.py validate_case --all              # every case (fairness + solvability)
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py spectacular --validate --fail-on-warn --file /dev/null
.venv/bin/pytest
```

```bash
# 6. Frontend (Vue 3 + Vite), with Django running on 8010 (step 4)
cd frontend
npm install
npm run dev                  # http://localhost:5180 (proxies /api, /admin, /static to :8010)

# 7. Frontend checks (the same ones CI runs)
npm run lint:check && npm run format:check && npm run type-check && npm test && npm run build-only
npm run api:types            # regenerate src/api/schema.d.ts after backend API changes
```

**Ports:** Casefile uses fixed dev ports (**Django 8010, Vite 5180, PostgreSQL 5436**), because the usual defaults (8000, 5173, 5432) are taken by other local projects. Vite uses `strictPort`, so a clash fails loudly instead of silently serving a different app.

Stop the database with `docker compose stop db`. `docker compose down -v` also deletes its data volume.

### Planned (later milestones)

> These steps describe the **intended** workflow. They don't work yet: `import_case` arrives in M4 and Playwright in M7+.

```bash
# Import a case into the database (backend venv from step 4)
cd backend
python manage.py import_case ../content/cases/the-missing-masterpiece --publish

# End-to-end tests
npx playwright test                # from repo root, with both servers running
```

## Documentation

| Document | Contents |
|---|---|
| [PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | Audience, gameplay loop, feature set, principles, **decisions (decided and open)** |
| [SCREEN_DESIGN.md](docs/SCREEN_DESIGN.md) | Navigation map and screen-by-screen specifications |
| [CASE_DESIGN.md](docs/CASE_DESIGN.md) | Case authoring format, fairness standards, example case |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, services, data flow, key decisions |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | PostgreSQL entities, relationships, constraints |
| [API_PLAN.md](docs/API_PLAN.md) | REST endpoints, permissions, request/response shapes |
| [UI_UX_GUIDELINES.md](docs/UI_UX_GUIDELINES.md) | Visual language, components, accessibility |
| [TESTING_PLAN.md](docs/TESTING_PLAN.md) | Test strategy across all layers, including mystery-logic validation |
| [DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) | Ordered milestones, dependencies, acceptance criteria |

## Adding a new case (planned workflow)

1. Copy `content/cases/_template/` to `content/cases/<your-slug>/`.
2. Write the player-visible content (`case.yaml`, `people.yaml`, `locations.yaml`, `evidence.yaml`, `interviews.yaml`, `timeline.yaml`, `accusation.yaml`) and the spoiler content (`spoilers/contradictions.yaml`, `spoilers/solution.yaml`), following [`docs/CASE_DESIGN.md`](docs/CASE_DESIGN.md).
3. Run `python manage.py validate_case <path>`. It checks references, the unlock graph, solvability, and the fairness rules.
4. Run `python manage.py import_case <path>`, then playtest. Publish with `--publish` when ready.

The process needs no new application code unless a case requires a new *mechanic* (see "Extending mechanics" in `docs/ARCHITECTURE.md`).

## License and content copyright

- **Application code** (backend, frontend, tests, tooling) and **technical documentation** (`docs/`): **MIT License**, in [`LICENSE`](LICENSE).
- **Case content** (original mystery narratives, characters, dialogue, evidence text, hints, solutions, and original artwork under `content/cases/`): **© the author, all rights reserved**, as set out in [`content/COPYRIGHT.md`](content/COPYRIGHT.md). This also covers the case narrative excerpts in `docs/CASE_DESIGN.md` §9–10. It may be read here but not reused or republished without permission, unless specific content is later explicitly licensed for reuse.
- Third-party images and assets keep their own licenses, listed in each case's `assets/CREDITS.md`.

## ⚠️ Spoiler warning

This repository is public. Case solutions live in `content/cases/*/spoilers/` and in parts of `docs/CASE_DESIGN.md`. If you want to play a case fairly, don't open those files first.

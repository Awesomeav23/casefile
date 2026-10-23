# Casefile

> An immersive mystery investigation platform. Read the briefing, walk the scene, question suspects, catch the lie, and name the culprit, with proof.

**Status: M0 complete (repository & tooling).** This repository contains the design documentation and the development tooling (local PostgreSQL, lint hooks, CI lint workflow). No application code exists yet. Every feature described below is *planned*, not implemented. See [the roadmap](docs/DEVELOPMENT_ROADMAP.md) for what comes next.

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
| Contradictions | Pair a statement with conflicting evidence to break an alibi and unlock new leads |
| Timeline | Reconstructed events by person and location, claimed vs. verified |
| Evidence board | Pin, arrange, and connect items; attach notes |
| Theories | Draft and compare competing theories |
| Accusation | Structured, evidence-backed final accusation |
| Results | Scored outcome, full solution, and the evidence you missed |
| Player progress | Solved cases, ratings, in-progress investigations, statistics |
| Case pipeline | YAML authoring format, validator, solvability checker, importer |

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 (Composition API, `<script setup>`), TypeScript, Vite, Vue Router, Pinia |
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| API schema | OpenAPI generated with drf-spectacular; TypeScript types generated from it |
| Testing | pytest + pytest-django (backend), Vitest + Vue Test Utils (frontend), Playwright (end-to-end) |
| CI | GitHub Actions (planned) |

Rationale is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Prerequisites

Pinned in M0:

| Tool | Version | Pinned in |
|---|---|---|
| Python | 3.13 | `.python-version` |
| Node.js | 22 LTS (with npm) | `.nvmrc` |
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
├── frontend/                # Vue 3 + TypeScript app (planned)
│   └── src/
├── content/
│   └── cases/               # One folder per mystery (YAML + assets)
│       └── the-missing-masterpiece/
└── e2e/                     # Playwright tests (planned)
```

## Setup

### Working now (M0: repository & tooling)

These commands were run and verified during M0:

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
```

Stop the database with `docker compose stop db`. `docker compose down -v` also deletes its data volume.

### Planned (later milestones)

> These steps describe the **intended** workflow. They don't work yet, because the backend arrives in M1, the frontend in M2, and cases from M3/M4.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # set DATABASE_URL, SECRET_KEY
python manage.py migrate
python manage.py validate_case ../content/cases/the-missing-masterpiece
python manage.py import_case   ../content/cases/the-missing-masterpiece --publish
python manage.py runserver

# Frontend
cd frontend
npm install
npm run dev                        # Vite dev server proxies /api to Django

# Tests
cd backend && pytest
cd frontend && npm run test
npx playwright test                # from repo root, with both servers running
```

## Documentation

| Document | Contents |
|---|---|
| [PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | Audience, gameplay loop, feature set, principles, **open decisions** |
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

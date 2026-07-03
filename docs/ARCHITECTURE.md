# NavigatorEdu — Architecture

This document explains how the pieces fit together and why they were chosen.
Target reader: a developer opening the repo for the first time.

## System overview

```
Browser
  │  static files (/, index.html)
  │  JSON over REST (/api/v1/*)
  ▼
FastAPI app (backend/app/main.py)
  ├── routers/reference.py   categories, items, search, disclaimers
  ├── routers/training.py    training notes (module-grouped lessons)
  ├── routers/cases.py       practice cases
  ├── routers/quiz.py        questions + server-side scoring
  ▼
SQLModel session (db.py)  ──►  SQLite (data/navigatoredu.db)
                                    ▲
                     seed.py  ──────┘
                        ▲
                data/seed.json  (content source of truth)
```

One process serves everything. There is no separate frontend server, no
reverse proxy, and no message queue — deliberately, because none of those
earn their complexity at this scale.

## Backend

- **FastAPI** with three routers, all under the `/api/v1` prefix. Versioning
  the prefix from day one makes a future `/api/v2` painless.
- **Dependency injection everywhere.** Every route receives its database
  session through `Depends(get_session)`. This is the seam the test suite
  uses: tests override that single dependency to point at an in-memory
  database, so tests exercise the real query code with zero mocking.
- **Lifespan startup** creates tables and auto-seeds an empty database, so
  `uvicorn backend.app.main:app` alone produces a working app on first run.

### Response-shaping rules

The API deliberately returns different shapes for list vs. detail views:

| Endpoint            | Omits                                | Why |
|---------------------|--------------------------------------|-----|
| `GET /items`        | `body_md`                            | Keep list payloads light |
| `GET /cases`        | `guided_steps`, `expected_outcome_md`| Answers revealed on demand in the UI |
| `GET /quiz`         | `correct_index`, `explanation`       | Answers must never reach the client before submission |

Quiz scoring is server-side (`POST /quiz/submit`): the client sends
`{question_id: selected_index}` and receives score, per-question correctness,
and explanations. A client-side quiz would leak every answer in the page
source.

## Frontend

A single `frontend/index.html` (~300 lines): Tailwind via CDN, a vanilla-JS
hash router, and a minimal markdown renderer. No build step.

- Routes: `#/` home, `#/categories`, `#/item/{id}`, `#/cases`, `#/case/{id}`, `#/training`, `#/quiz`.
- Served by the same FastAPI process via `StaticFiles`, mounted at `/` *after*
  the API routers so `/api/*` always wins.
- The markdown renderer handles the subset the seed content uses (headings,
  bold, italics, lists). It escapes HTML before rendering, so seed content
  cannot inject markup.

Trade-off: a React + build-step frontend would demonstrate different skills,
but a zero-dependency SPA keeps the run story to a single command and puts
the portfolio emphasis on the backend and data design.

## Database and models

Six SQLModel tables in `models.py`, mirroring the entities in `seed.json`:

`Category`, `Disclaimer`, `ReferenceItem`, `TrainingNote`, `PracticeCase`,
`QuizQuestion` — with foreign keys between them (items → categories,
questions → source items, etc.).

List-valued fields (`tags`, `options`, `guided_steps`, `related_item_ids`)
are stored as **JSON columns**. At this scale that is the honest choice:
simpler than join tables, still queryable, and trivially migratable later.

Search is hybrid: category filtering happens in SQL; free-text matching over
title/summary/tags happens in Python after the query. The upgrade path, if
the corpus grows, is SQLite FTS5 — noted in the code where it would go.

## Content packs and the seed process

All domain content lives in a self-contained JSON **content pack**. The
active pack is chosen by the `SEED_PATH` environment variable, resolved at
call time in `seed.get_seed_path()` (defaulting to `data/seed.json`).
Relative paths resolve against the project root, so the same value works
locally and in the container.

Three packs ship in `data/`: the Tidewatch Guild (celestial navigation),
the ArchiveGuild (archive apprenticeship), and CytoFISH Navigator (synthetic
FISH/cytogenetics *education*). They share one schema; switching packs changes
every page of the product without touching a line of code.

The CytoFISH pack is notable as a *specialized, safety-sensitive* domain: it
demonstrates that domain expertise can be encoded entirely in content while
every safety boundary (no PHI, no real cases, no diagnostic language) lives in
the pack and its disclaimers — never in the application code. The validator
and the pack tests are what let the project host such a domain confidently.
That is the strongest available proof that the models, routes, and frontend
encode *structure*, not content. Packs share an ID scheme, so switch on a
fresh database — the upserting seed would otherwise merge two domains.

The active pack is the single content source of truth. It is human-readable,
diff-friendly, and reviewable in a GitHub PR — properties a binary `.db`
file lacks.

`python -m backend.app.seed` (optionally with `SEED_PATH=...`):

1. Creates tables if missing.
2. Iterates collections in FK-safe order (disclaimers and categories first).
3. Uses `session.merge()` per row — upsert by primary key — so the script is
   **idempotent**: edit `seed.json`, re-run, and the database converges.

The generated `data/navigatoredu.db` is git-ignored; anyone can rebuild it.

## Content-pack validation

`backend/app/validate_pack.py` makes the pack format a real, enforced
interface rather than a convention. It checks — without touching the
database:

1. File exists and parses as JSON.
2. All six collections are present and are lists.
3. Every record has its required fields; IDs are unique per collection.
4. Foreign references resolve: items → categories/disclaimers, cases and
   questions → categories, questions → source items, training notes →
   related items.
5. Quiz sanity: options non-empty, `correct_index` in range.

The validator collects *all* problems before reporting (a content author
fixes one list, not one error per run) and exits 0/1/2 for valid /
invalid / unreadable. CI runs it against both shipped packs, so content
regressions fail the build exactly like code regressions.

Design note: validation is hand-rolled rather than JSON Schema. At six
collections it reads clearer, produces friendlier errors, and adds no
dependency; the docstring names JSON Schema as the upgrade path if the
format grows.

## API route reference

| Method | Route                     | Purpose |
|--------|---------------------------|---------|
| GET    | `/api/v1/categories`      | All categories |
| GET    | `/api/v1/items`           | Reference items; `?category=`, `?q=` filters |
| GET    | `/api/v1/items/{id}`      | Full item incl. markdown body |
| GET    | `/api/v1/disclaimers`     | Safety/synthetic-content notices |
| GET    | `/api/v1/training`        | Training notes, ordered by module + lesson |
| GET    | `/api/v1/cases`           | Practice cases (answers omitted) |
| GET    | `/api/v1/cases/{id}`      | Full case incl. guided steps + outcome |
| GET    | `/api/v1/quiz`            | Questions (answers omitted); `?category=` |
| POST   | `/api/v1/quiz/submit`     | Score answers; returns explanations |

Interactive docs: `/docs` (Swagger UI, generated by FastAPI).

## Testing

- `backend/tests/conftest.py` builds an **in-memory SQLite** engine
  (`StaticPool` so all connections share it), seeds it from the same
  `seed.json`, and overrides `get_session`.
- `backend/tests/test_api.py` covers every endpoint, including the two
  security-relevant behaviors: quiz answers never appear in `GET /quiz`, and
  scoring is computed server-side.
- Tests never touch the development database.

## Continuous integration

`.github/workflows/ci.yml`: checkout → Python 3.12 with pip caching →
`pip install -r requirements.txt` → `pytest -v`, on every push and PR. The
suite needs no services or secrets because the tests bring their own
in-memory database — which is what keeps the workflow this short.

## Docker

Single-stage image on `python:3.12-slim`, running as a non-root user.
`docker-compose.yml` mounts a named volume at `/app/data` so the SQLite file
persists across container restarts; the first run auto-seeds it. A compose
healthcheck polls `/api/v1/categories`.

## Extension points

- **New content:** edit a pack, re-run the seed script. No code changes.
- **New domain:** write one new content pack, run the validator, point
  `SEED_PATH` at it — the app re-skins entirely. Tested in
  `backend/tests/test_seed_path.py`.
- **New entity:** add a model, a seed collection entry, and a router — the
  three-file pattern is consistent across the codebase.
- **Postgres:** change the connection URL in `db.py`; SQLModel/SQLAlchemy
  abstracts the rest (JSON columns are supported on both).
- **Quiz history:** a `QuizAttempt` table plus persisting `POST /quiz/submit`
  results would add progress tracking without touching existing routes.

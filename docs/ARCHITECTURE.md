# NavigatorEdu — Architecture

How the pieces fit together and why they were chosen. Target reader: a
technical reviewer opening the repo for the first time.

Contents: [system overview](#system-overview) ·
[data flow](#data-flow) · [content-pack lifecycle](#content-pack-lifecycle) ·
[validation lifecycle](#validation-lifecycle) ·
[API and frontend](#api-and-frontend) · [database and models](#database-and-models) ·
[test strategy](#test-strategy) · [deployment and dev workflow](#deployment-and-dev-workflow) ·
[trade-offs and next steps](#trade-offs-and-next-steps)

## System overview

```
Browser
  │  static files (/, index.html)
  │  JSON over REST (/api/v1/*)
  ▼
FastAPI app (backend/app/main.py)
  ├── routers/reference.py   categories, items, search, disclaimers, pack-metadata
  ├── routers/training.py    training notes (module-grouped lessons)
  ├── routers/cases.py       practice cases
  ├── routers/quiz.py        questions + server-side scoring
  ▼
SQLModel session (db.py)  ──►  SQLite (data/navigatoredu.db)
                                    ▲
                     seed.py  ──────┘
                        ▲
              content pack (data/seed*.json — source of truth)
                        ▲
        new_pack.py (scaffold) · validate_pack.py (gate)
```

One process serves everything. There is no separate frontend server, no
reverse proxy, and no message queue — deliberately, because none of those
earn their complexity at this scale.

## Data flow

At runtime, every request follows the same path: the router receives a
session through `Depends(get_session)`, queries SQLite, shapes the response
(see [API and frontend](#api-and-frontend)), and returns JSON. The frontend
is a pure API consumer; it holds no content of its own.

Before runtime, content flows one way:

```
author edits pack ─► validate_pack (contract check, no DB)
                        ─► seed.py (clear-then-load into SQLite)
                             ─► app serves whatever the DB holds
```

The database is a build artifact — git-ignored and rebuildable from the pack
at any time. The pack, being human-readable JSON, is diff-friendly and
reviewable in a pull request; a binary `.db` file is neither.

## Content-pack lifecycle

All domain content lives in a self-contained JSON **content pack**. The
active pack is chosen by the `SEED_PATH` environment variable, resolved at
call time in `seed.get_seed_path()` (default `data/seed.json`; relative
paths resolve against the project root so the same value works locally and
in the container).

A pack's life:

1. **Scaffold** — `python -m backend.app.new_pack <slug>` emits a minimal,
   fully-wired pack that passes the validator immediately and carries the
   safety defaults (`synthetic_only: true`, educational-demo-only intended
   use, safety notes forbidding real records/cases and operational/clinical
   use). Slugs are constrained (`^[a-z][a-z0-9_]*$`) because they become both
   the filename and the `pack_id`; an existing file is never overwritten
   without `--force`.
2. **Author** — replace the `TODO` placeholder records with synthetic
   content. Schema and safety guidance: [CONTENT_AUTHORING.md](CONTENT_AUTHORING.md).
3. **Validate** — `python -m backend.app.validate_pack <file>` (details
   below).
4. **Seed** — `SEED_PATH=<file> python -m backend.app.seed` creates tables
   if missing, clears all existing content (children before parents, so FK
   constraints never trip), and loads only the selected pack — re-running
   after an edit converges the database, and switching packs is a single
   reseed. The pack's governance metadata lands in a single-row
   `PackMetadata` table (fixed `id=1`), so the metadata endpoint can never
   name a pack whose content is mixed with a stale one.
5. **Serve** — the app reports the loaded pack at
   `GET /api/v1/pack-metadata` and in the UI banner.

Because seeding clears first, two domains can never mix — the visible
content always matches the pack named by the metadata endpoint.

**Why metadata lives in a table rather than reading `SEED_PATH` at request
time:** the API then reports exactly what was *seeded*, not what an
environment variable happens to say now (the two can drift); it survives
restarts with no separate state file; and the endpoint stays identical in
shape to every other endpoint — a session query. The trade-off is that the
metadata is only as current as the last seed, which is the property we want:
the app describes the loaded database, and re-seeding is the deliberate act
that updates it.

## Validation lifecycle

`backend/app/validate_pack.py` makes the pack format a real, enforced
interface rather than a convention. Without touching the database, it
checks:

1. The file exists and parses as JSON.
2. The governance `metadata` object is present with all eight required
   fields, key fields non-empty, and `synthetic_only` exactly `true`.
3. All six content collections are present and are lists.
4. Every record has its required fields; IDs are unique per collection.
5. Foreign references resolve: items → categories/disclaimers, cases and
   questions → categories, questions → source items, training notes →
   related items.
6. Quiz sanity: options non-empty, `correct_index` in range.

The validator collects *all* problems before reporting — a content author
fixes one list, not one error per run — and exits 0/1/2 for
valid/invalid/unreadable, with errors written for content authors
(`quiz_questions 'q-003': correct_index 7 out of range for 4 options`).

Enforcement happens twice: a parametrized test sweeps every
`data/seed*.json` (new packs are picked up automatically), and CI runs the
validator CLI against each shipped pack on every push. Content regressions
fail the build exactly like code regressions.

Design note: validation is hand-rolled rather than JSON Schema. At six
collections it reads clearer, produces friendlier errors, and adds no
dependency; JSON Schema is the named upgrade path if the format grows.

## API and frontend

**API.** Versioned `/api/v1` prefix from day one (a future `/api/v2` is then
painless). Response shapes differ deliberately between list and detail
views:

| Endpoint            | Omits                                | Why |
|---------------------|--------------------------------------|-----|
| `GET /items`        | `body_md`                            | Keep list payloads light |
| `GET /cases`        | `guided_steps`, `expected_outcome_md`| Answers revealed on demand in the UI |
| `GET /quiz`         | `correct_index`, `explanation`       | Answers must never reach the client before submission |

Quiz scoring is server-side (`POST /quiz/submit`): the client sends
`{question_id: selected_index}` and receives score, per-question
correctness, and explanations. A client-side quiz would leak every answer in
the page source.

| Method | Route                     | Purpose |
|--------|---------------------------|---------|
| GET    | `/api/v1/categories`      | All categories |
| GET    | `/api/v1/items`           | Reference items; `?category=`, `?q=` filters |
| GET    | `/api/v1/items/{id}`      | Full item incl. markdown body |
| GET    | `/api/v1/disclaimers`     | Safety/synthetic-content notices |
| GET    | `/api/v1/training`        | Training notes, ordered by module + lesson |
| GET    | `/api/v1/pack-metadata`   | Active content pack's governance metadata |
| GET    | `/api/v1/cases`           | Practice cases (answers omitted) |
| GET    | `/api/v1/cases/{id}`      | Full case incl. guided steps + outcome |
| GET    | `/api/v1/quiz`            | Questions (answers omitted); `?category=` |
| POST   | `/api/v1/quiz/submit`     | Score answers; returns explanations |

Interactive docs: `/docs` (Swagger UI, generated by FastAPI).

**Frontend.** A single `frontend/index.html` (~530 lines): Tailwind via CDN,
a vanilla-JS hash router, and a minimal markdown renderer. No build step.
Served by the same FastAPI process via `StaticFiles`, mounted at `/` *after*
the API routers so `/api/*` always wins. The markdown renderer handles the
subset the packs use and escapes HTML before rendering, so pack content
cannot inject markup. The frontend reads `pack-metadata` to render the
active-pack banner and home card — the UI always names the loaded domain and
restates that it is synthetic-only.

Trade-off: a React + build-step frontend would demonstrate different skills,
but a zero-dependency SPA keeps the run story to a single command and puts
the portfolio emphasis on the backend and data design.

## Database and models

Seven SQLModel tables in `models.py`: the six content entities
(`Category`, `Disclaimer`, `ReferenceItem`, `TrainingNote`, `PracticeCase`,
`QuizQuestion`) with foreign keys between them, plus the single-row
`PackMetadata` governance record.

List-valued fields (`tags`, `options`, `guided_steps`, `related_item_ids`)
are stored as **JSON columns**. At this scale that is the honest choice:
simpler than join tables, still queryable, and trivially migratable later.

Search is hybrid: category filtering happens in SQL; free-text matching over
title/summary/tags happens in Python after the query. The upgrade path, if
the corpus grows, is SQLite FTS5 — noted in the code where it would go.

## Test strategy

- **One seam.** Every route receives its session through
  `Depends(get_session)`. `backend/tests/conftest.py` overrides that single
  dependency with an **in-memory SQLite** engine (`StaticPool` so all
  connections share it), seeded from the same pack format — so tests
  exercise the real query code with zero mocking, and the development
  database is never touched.
- **Coverage by concern.** `test_api.py` covers every endpoint including the
  two security-relevant behaviors (answers never in `GET /quiz`; scoring
  server-side). `test_seed_path.py` proves pack switching. `test_validate_pack.py`
  builds broken-pack fixtures by mutating a copy of the real default pack, so
  the tests stay valid as content evolves, and sweeps all shipped packs
  parametrically. `test_new_pack.py` exercises the scaffolder — slug rules,
  validator pass-through of generated packs, `--force` semantics, CLI exit
  codes — entirely in temp directories, so the suite never leaves a
  generated pack in `data/`.
- **87 tests**, all green in under a second, no services or secrets
  required — which is what keeps the CI workflow short.

## Deployment and dev workflow

**Local:** venv → `pip install -r requirements.txt` →
`python -m backend.app.seed` → `uvicorn backend.app.main:app --reload`.
Lifespan startup creates tables and auto-seeds an empty database, so the
first run works even without the explicit seed step.

**Docker:** single-stage image on `python:3.12-slim`, running as a non-root
user. `docker-compose.yml` mounts a named volume at `/app/data` so the
SQLite file persists across restarts; a compose healthcheck polls
`/api/v1/categories`. `SEED_PATH` selects the pack; reset the volume
(`docker compose down -v`) when switching.

**CI:** `.github/workflows/ci.yml` — checkout → Python 3.12 with pip caching
→ install → `pytest -v` → `validate_pack` against every shipped pack, on
every push and PR.

**Milestone workflow:** the project is developed in sequential milestones,
each starting from a fresh clone of the pushed repo, delivered with tests
and docs updated, and packaged as a versioned artifact. The commit history
mirrors the milestone sequence.

## Trade-offs and next steps

Each current choice is the honest one at this scale, with a named upgrade
path:

| Choice | Why now | Upgrade path |
|--------|---------|--------------|
| JSON columns for list fields | Simpler than join tables; still queryable | Proper join tables if relational queries over lists are needed |
| Linear-scan text search | Corpus is small; code stays obvious | SQLite FTS5 |
| Hand-rolled validation | Clearer errors, zero deps at six collections | JSON Schema if the format grows |
| No-build-step frontend | One-command run story; emphasis on backend | React + build if UI depth becomes the point |
| SQLite | Zero-config, perfect for a reviewer-runnable demo | Postgres via a connection-string change (JSON columns work on both) |
| No auth / user state | Out of scope; every service dilutes the signal | `QuizAttempt` table + persisted submissions would add progress tracking without touching existing routes |

Extension points, in the order they'd likely land: UI polish, an in-app pack
selector, FTS-backed search, exportable learning reports, a deployment
target — see [ROADMAP.md](ROADMAP.md). Adding a new *domain* requires no
code at all: scaffold with `new_pack`, author, validate, point `SEED_PATH`
at it.

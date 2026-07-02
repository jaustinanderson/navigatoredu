# NavigatorEdu ⚓

![CI](https://github.com/jaustinanderson/navigatoredu/actions/workflows/ci.yml/badge.svg)

A full-stack reference and training web app for a **fictional** knowledge
domain — the celestial-navigation practices of the invented *Tidewatch
Guild*. Built as a portfolio project demonstrating clean API design,
structured data modeling, testing discipline, and education-product thinking.

> **Synthetic-content statement:** every record in this application is
> fictional, written for this demo. There are no real organizations, people,
> or operational procedures here, and nothing is suitable for real-world
> navigation or training. The disclaimer is part of the schema (a
> `Disclaimer` table + `is_synthetic` flags), not just this paragraph.

## Problem statement

Specialized fields need learning tools that combine three things: searchable
reference material, scenario-based practice, and self-assessment — all backed
by one coherent data model. This project builds that product shape
end-to-end. The domain is deliberately fictional so the engineering can be
evaluated without proprietary content, and to prove the architecture is
domain-agnostic: swapping one JSON file re-skins the entire app.

## Features

- 📚 **Reference library** — categorized, tagged, searchable items with
  markdown bodies
- 🎓 **Training modules** — short ordered lessons, cross-linked to reference
  items
- 🧭 **Practice cases** — scenarios with reveal-as-you-go guided steps and
  expected outcomes
- ✅ **Quiz mode** — server-side scoring; answers never reach the client
  before submission
- 🗂 **Content pipeline** — human-reviewable `seed.json` → idempotent import
  script → SQLite
- 📄 **Auto-generated API docs** at `/docs`
- 🐳 **One-command Docker run**, 🔁 **CI running the full test suite**

## Architecture overview

```
Browser ── static SPA (/) + JSON REST (/api/v1/*)
   │
FastAPI (one process)
   ├── routers: reference · training · cases · quiz
   └── SQLModel session (DI) ──► SQLite
                                    ▲
                       seed.py ◄── data/seed.json  (source of truth)
```

Full detail, including the trade-offs and their upgrade paths:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Data model

| Table          | Purpose                              | Notable fields |
|----------------|--------------------------------------|----------------|
| Category       | Content taxonomy                     | `parent_id` (self-FK, nesting-ready) |
| ReferenceItem  | Core library entries                 | `tags` (JSON), `difficulty`, `disclaimer_id` |
| TrainingNote   | Ordered lessons grouped by module    | `related_item_ids` (JSON) |
| PracticeCase   | Scenario + guided steps + outcome    | answer fields hidden in list views |
| QuizQuestion   | MCQ with explanation                 | `correct_index` never serialized on GET |
| Disclaimer     | Safety/synthetic-content notices     | `applies_to` scope |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app.seed        # builds data/navigatoredu.db from seed.json
```

## Run

```bash
uvicorn backend.app.main:app --reload
```

- App: <http://127.0.0.1:8000>
- API docs: <http://127.0.0.1:8000/docs>

First run auto-seeds an empty database; the explicit seed script is for
re-importing after you edit `seed.json` (it upserts, so re-running is safe).

## Docker

```bash
docker compose up --build
```

That's the whole story: the image bundles the app and `seed.json`, the
database auto-seeds on first start, and a named volume (`navigatoredu-data`)
persists it across restarts. The container runs as a non-root user and has a
healthcheck against the API. Plain Docker, if you prefer:

```bash
docker build -t navigatoredu .
docker run -p 8000:8000 navigatoredu
```

## Tests

```bash
python -m pytest        # 17 tests
```

Tests run against an **isolated in-memory SQLite database** seeded from the
same `seed.json`, injected by overriding the one `get_session` dependency —
real queries, zero mocks, and your development database is never touched.

## CI

`.github/workflows/ci.yml` runs the full pytest suite on every push and pull
request (Ubuntu, Python 3.12, cached pip). Update the badge URL at the top of
this file with your GitHub username after pushing.

## Screenshots

See [screenshots/README.md](screenshots/README.md) for the capture checklist.

## Roadmap

- SQLite FTS5 search once the corpus outgrows linear scan
- Quiz sessions with persisted attempt history
- Content authoring CLI (validate + lint `seed.json`)
- Postgres profile in docker-compose for a production-shaped variant

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how it's built and why
- [docs/PORTFOLIO_CASE_STUDY.md](docs/PORTFOLIO_CASE_STUDY.md) — how to
  present this project professionally

## License

Portfolio/education demo. All content fictional.

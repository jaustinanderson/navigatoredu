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
  ├── routers/packs.py       allowlisted local-demo pack browser/selector
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
   name a pack whose content is mixed with a stale one. As its final step,
   seeding rebuilds the FTS5 search index from exactly what was loaded.
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

### The Content Pack Browser (local-demo selector)

`routers/packs.py` + `pack_registry.py` let a reviewer flip between the
bundled domains from the UI — the content-pack architecture made visible in
one click. Design boundaries, all deliberate:

- **Hard-coded allowlist.** `pack_registry.REGISTRY` maps three slugs to
  bundled seed files. A submitted slug is only ever used as a dictionary
  key — never as a path fragment — so no request can make the server read
  an arbitrary file. There is no scanning, no upload, and no user-supplied
  path anywhere in the feature.
- **No filesystem information leaves the server.** `GET /api/v1/packs`
  returns slugs plus each pack's own governance metadata (read live from
  the pack file, so the listing can't drift from the content). Unknown
  slugs get a 404 that reflects nothing back.
- **Reseed is the switch.** `POST /packs/select` calls the same
  clear-then-load `seed()` the CLI uses, through the same injected session,
  so tests exercise it against isolated databases and the metadata endpoint
  always names exactly what's loaded.
- **Intentionally not an admin feature.** A general content-management
  surface would need authentication, audit, and storage design — out of
  scope for a single-process portfolio demo, and diluting its signal. The
  browser demonstrates the architecture; the `SEED_PATH` CLI remains the
  canonical loading path outside the browser.

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

**Learning reports** (`POST /quiz/report`, `backend/app/report.py`) take the
same payload and return a complete, self-contained HTML document — inline
CSS only, no external assets, print-friendly — summarizing the attempt:
active-pack governance metadata, score, and per-question submitted answer,
correct answer, status, explanation, and related reference title. The report
is generated **statelessly** from the request: no accounts, no persistence,
no new tables, no stored history. That is a design position, not a gap — a
learner keeps the artifact by downloading it, the no-auth constraint stays
intact because nothing exists server-side to protect, and the footer says so
plainly ("Generated locally from submitted answers; not stored"). Every
dynamic value — pack metadata, question text, options, explanations,
reference titles, and the submitted values themselves — is HTML-escaped, and
an escaping test injects script payloads into every one of those fields to
prove none survive.

| Method | Route                     | Purpose |
|--------|---------------------------|---------|
| GET    | `/api/v1/categories`      | All categories |
| GET    | `/api/v1/items`           | Reference items; `?q=` (FTS5), `?tag=`, `?difficulty=`, `?category=` |
| GET    | `/api/v1/items/{id}`      | Full item incl. markdown body |
| GET    | `/api/v1/disclaimers`     | Safety/synthetic-content notices |
| GET    | `/api/v1/training`        | Training notes, ordered by module + lesson |
| GET    | `/api/v1/pack-metadata`   | Active content pack's governance metadata |
| GET    | `/api/v1/packs`           | Allowlisted bundled demo packs + which is active |
| POST   | `/api/v1/packs/select`    | Reseed the local demo DB from an allowlisted pack |
| GET    | `/api/v1/cases`           | Practice cases (answers omitted) |
| GET    | `/api/v1/cases/{id}`      | Full case incl. guided steps + outcome |
| GET    | `/api/v1/quiz`            | Questions (answers omitted); `?category=` |
| POST   | `/api/v1/quiz/submit`     | Score answers; returns explanations |
| POST   | `/api/v1/quiz/report`     | Printable self-contained HTML learning report (stateless) |

Interactive docs: `/docs` (Swagger UI, generated by FastAPI).

**Frontend.** A single `frontend/index.html` (~1,000 lines): Tailwind via CDN,
a vanilla-JS hash router, and a minimal markdown renderer. No build step.
Served by the same FastAPI process via `StaticFiles`, mounted at `/` *after*
the API routers so `/api/*` always wins. The markdown renderer handles the
subset the packs use and escapes HTML before rendering, so pack content
cannot inject markup. The frontend reads `pack-metadata` to render the
active-pack banner and home card — the UI always names the loaded domain and
restates that it is synthetic-only.

The router's one purely static view is the **Reviewer guide** (`#/guide`,
v20): a self-contained walkthrough for evaluating the project in 3–5
minutes — what the app is, the demo path to follow, the technical details
worth noticing, the safety boundaries, and CTA cards into every section
plus the API docs, case study, and retrospective. It deliberately makes no
API calls, because it is the page a reviewer may read *before*
understanding anything else, and it reuses the app's existing components
(`linkCard`, section/heading structure) rather than introducing a second
visual language. Landing there also added `aria-current="page"` to the
active-nav logic, so the current section is announced to assistive
technology, not just underlined for sighted users. Its structure, CTA
targets, keyboard operability, and axe cleanliness are all pinned by tests.

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

Free-text search is **SQLite FTS5** (`backend/app/search.py`): a virtual
table over title, summary, body text, and tags, queried through
`GET /items?q=` with bm25 rank ordering, token + trailing-prefix matching,
and case-insensitivity from the unicode61 tokenizer. User input is
phrase-quoted token by token, so FTS query operators in user input are
inert. Tag filtering is exact JSON-array membership evaluated in SQL
(`json_each`); difficulty and category are column equality. Filters combine
as AND.

The index is **rebuilt from scratch at the end of every seed**. Seeding is
the only content write path (CLI, `SEED_PATH`, and the pack browser all call
the same `seed()`), so rebuild-at-seed keeps search exactly in sync with the
active pack with no trigger machinery — stale search results across pack
switches are structurally impossible. One documented safety fallback: on a
database that has never been seeded (so the FTS table doesn't exist), search
returns no matches instead of erroring; there is no second search
implementation. This replaced the original in-Python linear scan — the
upgrade path named in the code since v02 — and it is still local demo
search over synthetic packs, not production search infrastructure (no
ranking tuning, no highlighting).

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
- **159 tests**, all green in about a second, no services, network, or
  secrets required — which is what keeps the CI workflow short. (The v22
  deploy-smoke unit tests belong to this suite too: they exercise
  `scripts/smoke_deploy.py` through an injected fake HTTP transport.)

### Accessibility audit (browser layer)

`tests/browser/accessibility.spec.js` runs axe-core (via
`@axe-core/playwright`, dev-only) against the five primary views — Home,
Reference, Packs, Quiz, and the Reviewer guide — rendered in the same self-starting Playwright
setup as the behavior tests, against a deterministic pack so contrast and
content findings are reproducible. Design decisions:

- **Full default ruleset, no exclusions.** No rules disabled, no elements
  excluded from the scan; there is nothing to keep in sync with the markup.
- **Fail threshold = serious/critical.** Those axe impact tiers map to
  defects that block or badly degrade assistive-technology use.
  Minor/moderate findings do not fail CI but are printed as advisories in
  the test output, so they stay visible until triaged instead of
  disappearing into a suppression list. (At v18 the four views scan clean
  at every level — the threshold is policy for the future, not a carve-out
  for present debt.)
- **Scan after real render.** Each test waits for the async content
  (chips, category sections, pack cards, quiz fieldsets) before scanning,
  so the audit sees the page users interact with, not the loading state.
- **Contrast floor for muted text.** `text-slate-600` (#475569) is the
  lightest tone used for readable text: ≥7:1 on white and on the `foam`
  page background. `slate-400`/`slate-500` proved below WCAG AA in the
  audit's first CI run (2.56:1 and 4.39:1 respectively) and are no longer
  used anywhere — visible text and the search placeholder alike sit at
  `slate-600` or darker. Inline links inside body
  text are underlined, not distinguished by color alone, and the markdown
  renderer normalizes heading levels relative to the enclosing heading so
  rendered documents never skip a level.

**Known boundaries, stated plainly:** axe automates only the mechanically
checkable subset of WCAG. Screen-reader interaction quality is not covered,
and detail views (reference item, practice case) reuse the same templates
as the scanned views and were left out to keep the audit at one
representative scan per template family — they inherit, rather than
independently prove, the clean result. These are the documented next
increments if the accessibility bar is raised further.

### Keyboard journeys (browser layer)

`tests/browser/keyboard.spec.js` (v19) is the deliberate complement to the
axe scans: axe proves the page's *properties* (names, roles, contrast,
landmarks); the keyboard suite proves its *operation* — that a person
without a mouse can actually complete the app's main tasks. Five journeys
cover main-nav reachability and activation, Reference search + tag +
difficulty filtering + Clear all, pack switching with stale-content
assertions, the full quiz through report download (file verified), and
focus visibility. Design decisions:

- **Real keyboard events only.** Tab / Shift+Tab / Enter / Space via
  Playwright's keyboard API; no `.click()` and no programmatic `.focus()`
  inside the journeys. The one setup exception is pack selection through
  the API, which arranges server state and is not part of the journey
  under test.
- **Reachability by bounded tabbing.** A helper presses Tab until the
  target is the active element, capped at 40 presses — so a focus trap or
  keyboard-unreachable control fails with a message naming where focus
  actually ended up, instead of hanging or silently cheating with
  `element.focus()`.
- **Invariant-based focus assertions.** Keyboard focus must produce a
  solid outline of measurable width (the `:focus-visible` rule), absent at
  rest. Style-based, polled, no exact-RGB checks — the same lesson the
  chip suite learned from mid-transition frames. One Chromium quirk is
  encoded in the test: computed `outline-width` reports 3px even when
  `outline-style: none`, so "no indicator" is asserted on style, not width.

The v19 run found **no frontend bugs to fix** — the journeys pass on the
existing markup because it is built from native elements (real `<button>`,
`<input type=radio>`, hash `<a>` links) that carry correct keyboard
behavior for free. That is itself the architectural point: semantic HTML
is the cheapest accessibility investment in the codebase.

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

**CI:** `.github/workflows/ci.yml` — three jobs on every push and PR.
`test`: checkout → Python 3.12 with pip caching → install → `pytest -v` →
`validate_pack` against every shipped pack. `docker-build`: builds the image
from a clean checkout and smoke-tests it (curl against `/api/v1/categories`
and `/api/v1/pack-metadata` in the running container) — a packaging proof,
deliberately not deployment: no push, no registry, no secrets.
`browser-test`: the Playwright suite (behavior, accessibility audit,
keyboard journeys) against a self-started instance — see "Test strategy"
above.

**Deployment option (Render):** `render.yaml` is a declarative blueprint a
reviewer can deploy from a fork in the browser — free tier, no CLI, no
secrets — consuming the same Dockerfile. The container `CMD` honors the
platform-injected `PORT` with a local default of 8000, so one image serves
compose and Render identically. `SEED_PATH` selects the bundled pack at
deploy time. Design positions, held on purpose: `autoDeploy: false` (a
portfolio demo warrants a build check, not CD), no added auth (there is no
user data to protect — the report feature is stateless by design), and no
persistence beyond the demo SQLite file (ephemeral free-tier disks simply
re-seed on restart, which is the same clear-then-load behavior the app has
everywhere). Deployment readiness here is evidence the container story is
real — not an invitation to treat a synthetic demo as production.

**Hosted smoke checks (deployment verification, v22):** every check layer
above proves something about the *code*: pytest proves the logic, the
browser suite proves the UI, `docker-build` proves the image packages. None
of them can prove that a specific deployed URL — spun up from a fork, on an
ephemeral free tier, possibly weeks ago — is still alive, still serving the
expected pack, and still declaring its synthetic-only posture.
`scripts/smoke_deploy.py` is that last layer: a standard-library-only
script that runs a read-only checklist against a live instance (home page,
`/api/v1/pack-metadata` including the `synthetic_only` flag and an optional
`--expected-pack-id` pin, categories, items, the OpenAPI schema advertising
the report endpoint, and one stateless empty-payload `POST
/api/v1/quiz/report` round-trip), prints pass/fail per check, and exits
nonzero on any failure. It writes nothing to the target — the report
endpoint is stateless by design, which is what makes a smoke POST safe.
A manual `workflow_dispatch` workflow
(`.github/workflows/hosted-smoke.yml`) runs the same script from GitHub
with a URL input and no secrets; it deploys nothing, preserving the
project's no-CD stance. The script's transport is one injectable `fetch`
callable, so its unit tests run in the ordinary pytest suite with the HTTP
boundary faked — CI never needs network access to a live deployment.

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
| ~~Linear-scan text search~~ | Shipped the upgrade path in v13: FTS5, rebuilt per seed | Ranking tuning / highlighting if search becomes a product surface |
| Hand-rolled validation | Clearer errors, zero deps at six collections | JSON Schema if the format grows |
| No-build-step frontend | One-command run story; emphasis on backend | React + build if UI depth becomes the point |
| SQLite | Zero-config, perfect for a reviewer-runnable demo | Postgres via a connection-string change (JSON columns work on both) |
| No auth / user state | Out of scope; every service dilutes the signal | `QuizAttempt` table + persisted submissions would add progress tracking without touching existing routes |

Extension points, in the order they'd likely land: UI polish, an in-app pack
selector and FTS search (both shipped), exportable learning reports, a deployment
target — see [ROADMAP.md](ROADMAP.md). Adding a new *domain* requires no
code at all: scaffold with `new_pack`, author, validate, point `SEED_PATH`
at it.

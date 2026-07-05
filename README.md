# NavigatorEdu ⚓

![CI](https://github.com/jaustinanderson/navigatoredu/actions/workflows/ci.yml/badge.svg)

**A full-stack learning platform where the entire knowledge domain is a
swappable, validated JSON content pack.** One codebase (FastAPI + SQLite +
vanilla-JS SPA) hosts three complete demo domains — including a fully
synthetic cytogenetics/FISH education pack — switched by a single environment
variable, with governance metadata and content validation enforced in CI.

> **Synthetic-content statement:** every record in this application is
> fictional, written for this demo. There are no real organizations, people,
> patients, cases, or operational procedures here, and nothing is suitable for
> real-world, operational, or clinical use. That statement is enforced by the
> system itself: each pack must declare `synthetic_only: true` in governance
> metadata that the validator checks on every CI run.

## What this is, in 30 seconds

- **What:** a reference-library / training-module / practice-case / quiz web
  app whose content is entirely data — a JSON "content pack" loaded into
  SQLite by an idempotent seed script.
- **Why:** to demonstrate, concretely, that structure and content can be
  fully separated: swapping one file re-skins the whole product with zero
  code changes.
- **The problem it solves:** specialized fields need learning tools that
  combine searchable reference material, scenario practice, and
  self-assessment over one coherent data model — and content-driven systems
  need their content held to the same rigor as code.
- **Skills shown:** REST API design, relational data modeling, test-driven
  development (137 tests, no mocks), data validation and governance, CI/CD
  basics, Docker, and safe modeling of a sensitive domain using synthetic
  content.

## Portfolio value

This project is built to be read by employers. It maps to real work in:

- **Clinical laboratory informatics** — the CytoFISH pack shows a
  specialized, safety-sensitive domain (cytogenetics/FISH education concepts)
  hosted on a generic platform, with every safety boundary carried in the
  content and its governance metadata rather than bolted onto code. This is a
  demonstration of domain interest and safe-data discipline, not a clinical
  tool or a claim of clinical validity.
- **Structured educational content systems** — categories, reference items,
  ordered training modules, guided practice cases, and server-scored quizzes
  over one relational model; the shape of an LMS or documentation platform in
  miniature.
- **Validation and governance** — a CLI validator enforces the pack contract
  (structure, references, quiz sanity, and required provenance/intended-use
  metadata) and runs in CI, so a content edit that breaks the contract fails
  the build exactly like a code regression.
- **Data-backed UI/API workflows** — versioned REST endpoints with deliberate
  list/detail response shaping; the frontend and Swagger docs both consume
  the same API.
- **Test-driven development** — 87 pytest tests against isolated in-memory
  databases through one dependency-injection seam; real queries, zero mocks.
- **Content-pack architecture** — the load-bearing idea behind white-label
  products, LMS platforms, and documentation systems: identify the invariant
  structure beneath a domain and keep it out of the code.
- **Safe synthetic domain modeling** — inventing realistic-shaped but fully
  fictional content, stating its boundaries in disclaimers and metadata, and
  enforcing the synthetic-only invariant mechanically.

### Why the CytoFISH pack matters

CytoFISH Navigator is the strongest single artifact in the repo for a career
direction toward clinical laboratory informatics. It shows two things at
once: familiarity with the *shape* of cytogenetics/FISH education content
(panels, probes, signal-pattern reasoning, review and escalation habits), and
the judgment to model that domain **safely** — no PHI, no real cases, no
accession numbers, no protocols, no diagnostic language, with those
exclusions written into the pack's own disclaimers and `safety_notes`. In
regulated fields, knowing what to leave out is as important as knowing what
to include; this pack demonstrates that instinct without overclaiming any
clinical capability.

## Technical highlights

| Area | What's here |
|------|-------------|
| Backend | **FastAPI**, versioned `/api/v1` routers, dependency-injected sessions |
| Data | **SQLModel / SQLite**; six related tables; JSON columns for list fields; **FTS5 full-text search** over reference items, rebuilt on every seed |
| Testing | **Pytest** — 137 tests on isolated in-memory DBs via one DI override; no mocks |
| CI | **GitHub Actions** — pytest + pack validation, Docker build check, and Playwright browser tests, on every push/PR |
| Ops | **Docker** (non-root image, PORT-aware) + compose volume and healthcheck; **Render blueprint** for deploy-it-yourself hosting |
| Content pipeline | **Content-pack validator** (`validate_pack`) gating CI; **SEED_PATH**-based pack switching; **authoring command** (`new_pack`) scaffolding valid, safe-by-default packs |
| Governance | **Pack-metadata endpoint** (`GET /api/v1/pack-metadata`) reporting exactly what was seeded; active pack shown in the UI banner |
| Pack browser | **Allowlisted local-demo selector** (`/api/v1/packs` + Packs page) — flip between the bundled domains from the UI; no paths, no uploads |
| Learning reports | **Stateless exportable reports** (`POST /api/v1/quiz/report`) — printable, self-contained HTML per quiz attempt; no accounts, nothing persisted |
| Frontend | Single-file vanilla-JS SPA (Tailwind via CDN, hash router, HTML-escaped markdown rendering) — a deliberate no-build-step demo UI |
| Domains | Three validated packs: Tidewatch Guild (celestial navigation), ArchiveGuild (archive apprenticeship), **CytoFISH Navigator** (synthetic cytogenetics/FISH education) |

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app.seed        # builds data/navigatoredu.db from seed.json
uvicorn backend.app.main:app --reload
```

- App: <http://127.0.0.1:8000>
- API docs: <http://127.0.0.1:8000/docs>

First run auto-seeds an empty database; the explicit seed script is for
re-importing after editing a pack, and for switching packs (seeding
clears the content tables first, then loads only the selected pack).

Or with Docker:

```bash
docker compose up --build
```

## Live demo / deployment

**Local run is the primary demo path** — this project is built to be cloned
and running in under a minute. For reviewers who want a hosted look, the
repo includes a one-file deployment blueprint for **Render** (chosen for
simplicity: free tier, deploys from a GitHub fork in the browser, no CLI,
no payment method, and it consumes the existing Dockerfile unchanged).

Deploy it yourself:

1. Fork this repository.
2. In the Render dashboard: **New → Blueprint**, select your fork. Render
   reads [`render.yaml`](render.yaml) and builds the Dockerfile.
3. Optionally set the `SEED_PATH` environment variable to choose which
   bundled pack the instance serves:

   | Pack | `SEED_PATH` value |
   |------|-------------------|
   | Tidewatch Guild (default) | `data/seed.json` |
   | ArchiveGuild | `data/seed_archiveguild.json` |
   | CytoFISH (synthetic) | `data/seed_cytofish_synthetic.json` |

Scope and safety, stated plainly: a deployed instance serves **only the
bundled synthetic packs** — the allowlisted selector cannot load anything
else, there are no uploads and no user data, and all content remains
fictional. **No real clinical use, no PHI, no real patient data**, on the
server exactly as locally. There is deliberately no auth (nothing to
protect), no persistence beyond the demo SQLite file (free-tier disks are
ephemeral; the app re-seeds `SEED_PATH` on every start, so UI pack switches
last until the next restart — expected demo behavior), and **no continuous
deployment** (CI includes a Docker *build check* only; `autoDeploy` is off
in the blueprint).

## Demo the CytoFISH pack

Easiest way: open **Packs** in the running app and click **Load demo
pack** — a local-demo selector that reseeds from one of the three bundled,
allowlisted packs and refreshes the UI (no arbitrary paths, no uploads;
details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

The command-line workflow works unchanged, and is the canonical way outside
the browser. Switching is a single reseed — the seed script clears existing
content before loading, so the database always holds exactly one pack:

```bash
SEED_PATH=data/seed_cytofish_synthetic.json python -m backend.app.seed
SEED_PATH=data/seed_cytofish_synthetic.json uvicorn backend.app.main:app --reload
```

Open <http://127.0.0.1:8000> — the banner and home card name the active pack
and restate that it is synthetic-only. The raw governance metadata is at
`/api/v1/pack-metadata`. The other packs work the same way with their file in
`SEED_PATH` (`data/seed.json` is the default; `data/seed_archiveguild.json`
is the third domain).

## Validate all content packs

```bash
python -m backend.app.validate_pack data/seed.json
python -m backend.app.validate_pack data/seed_archiveguild.json
python -m backend.app.validate_pack data/seed_cytofish_synthetic.json
```

The validator checks structure, required fields, unique IDs, foreign
references, quiz-answer sanity, and the governance metadata (including the
`synthetic_only: true` invariant). It collects all problems before reporting
and exits 0/1/2 for valid/invalid/unreadable. CI runs it on every push.

## Create a new content pack

```bash
python -m backend.app.new_pack demo_pack        # → data/seed_demo_pack.json
python -m backend.app.new_pack demo_pack --force # regenerate (overwrite)
```

The scaffolder emits a minimal, fully-wired pack that passes the validator
immediately and ships safe-by-default (`synthetic_only: true`,
educational-demo-only intended use, safety notes forbidding real records,
real cases, and operational or clinical use). Edit the `TODO` placeholder
records, validate, seed, run. Full schema and workflow:
[docs/CONTENT_AUTHORING.md](docs/CONTENT_AUTHORING.md).

## 60-second demo script

The home page carries this walkthrough on-screen (hero → **Start reviewer
walkthrough**), with a "Notice:" line per step telling the reviewer what each
step proves. The canonical order:

1. **Home** — hero states what the app is; the active-pack manifest card
   shows the loaded domain's governance metadata (intended use, safety
   notes, synthetic-only badge), served by `GET /api/v1/pack-metadata`.
2. **Packs → Load a different pack** — one click reseeds the local demo
   database from an allowlisted bundled pack. The banner and manifest change
   immediately.
3. **Reference** — the entire domain has changed with zero code changes.
   This is the moment to judge: the content-pack architecture made visible.
   Search is FTS5-backed (try a partial word — prefix matching works), and
   tag/difficulty chips narrow results server-side.
4. **A practice case** — guided steps reveal one at a time; answer material
   is omitted from list endpoints and fetched on demand.
5. **Quiz → check answers** — scoring happens server-side; correct answers
   never appear in the page source before submission. Then **Download
   report**: a self-contained, printable HTML summary of the attempt,
   generated statelessly from the submitted answers — nothing is stored.
6. **`/docs`** — the same API, self-documenting via OpenAPI.
7. **Close on validation and CI** — every content pack is checked by
   `validate_pack` on every push: structure, references, quiz sanity, and
   required governance metadata. Content is held to the same contract
   discipline as code.

The home page also states what the project demonstrates, what is
intentionally out of scope (no clinical use, no PHI, no uploads, no
auth/AI), and the tech stack — so a reviewer gets positioning, safety
posture, and demo path without opening a single doc. The full multi-pack
walkthrough (including CLI switching and a screenshot checklist) is in
[docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

## Data model

| Table          | Purpose                              | Notable fields |
|----------------|--------------------------------------|----------------|
| Category       | Content taxonomy                     | `parent_id` (self-FK, nesting-ready) |
| ReferenceItem  | Core library entries                 | `tags` (JSON), `difficulty`, `disclaimer_id` |
| TrainingNote   | Ordered lessons grouped by module    | `related_item_ids` (JSON) |
| PracticeCase   | Scenario + guided steps + outcome    | answer fields hidden in list views |
| QuizQuestion   | MCQ with explanation                 | `correct_index` never serialized on GET |
| Disclaimer     | Safety/synthetic-content notices     | `applies_to` scope |
| PackMetadata   | Single-row record of the seeded pack | `synthetic_only`, `intended_use`, `safety_notes` |

## Tests

```bash
python -m pytest        # 137 tests
```

Tests run against an **isolated in-memory SQLite database** seeded from the
same pack format, injected by overriding the one `get_session` dependency —
real queries, zero mocks, and the development database is never touched.

### Browser tests (Playwright)

Pytest covers backend and data invariants; a separate **Playwright** suite
covers the UI-behavior layer a headless harness can't see — added because
the two bugs manual review caught (blank filter chips, stale categories
after pack switching) both lived in exactly that layer. Twelve tests cover
chip readability via real computed styles (at rest, selected, after Clear
all), search/tag/difficulty/combined filtering, pack switching through the
Packs UI with stale-content assertions, the quiz report download (file
contents verified, `<script>`-free), and an API-docs smoke.

```bash
npm install
npx playwright install --with-deps chromium
npm run test:browser
```

The config starts the app itself on a test port after reseeding a fresh
demo database (`data/navigatoredu.db` is a rebuildable artifact, so this is
lossless). Dev/test-only: the app has no runtime Node dependency, and CI
runs the suite in its own `browser-test` job. All content exercised remains
the bundled synthetic packs.

## Screenshots and docs

- [screenshots/](screenshots/) — captured views of all three packs;
  [screenshots/README.md](screenshots/README.md) is the capture checklist
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design, data flow,
  lifecycles, and trade-offs
- [docs/PORTFOLIO_CASE_STUDY.md](docs/PORTFOLIO_CASE_STUDY.md) — the project
  as a professional case study
- [docs/RETROSPECTIVE.md](docs/RETROSPECTIVE.md) — the project as an
  engineering story: v01–v15 narrative, the three major bugs and how they
  were diagnosed, and the lessons that changed the architecture
- [docs/INTERVIEW_TALKING_POINTS.md](docs/INTERVIEW_TALKING_POINTS.md) —
  concise interview preparation for this project
- [docs/CONTENT_AUTHORING.md](docs/CONTENT_AUTHORING.md) — pack schema and
  the create → validate → seed → run workflow
- [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) — local walkthrough of all three
  packs and what to screenshot
- [docs/ROADMAP.md](docs/ROADMAP.md) — realistic next milestones

## License

Portfolio/education demo. All content fictional and synthetic.

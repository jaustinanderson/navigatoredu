# NavigatorEdu — Demo Guide

A step-by-step script for demonstrating NavigatorEdu locally, including how to
switch between the three content packs and what to capture for a portfolio
walkthrough.

Each pack is loaded by seeding the database from a different JSON file via the
`SEED_PATH` environment variable. The application code never changes — only the
content does. The home page and top banner display the **active content pack**
so it is always clear which domain is loaded.

As of v13, Reference search is FTS5-backed with tag and difficulty filter
chips — during the Reference beat, type a partial word (prefix matching) and
click a tag chip to show server-side filtering; the active-filter bar and
"Clear all" make the state obvious.

As of v12, the home page is a self-guiding reviewer landing: a hero with
three calls to action, the on-screen **Reviewer walkthrough** (six steps,
each with a "Notice:" line saying what that step proves), a "What this
demonstrates" grid, an "Intentionally out of scope" card, and the tech
stack. When demoing live, you can simply follow the home page top to
bottom — the narration below adds the spoken framing.

## One-time setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Switching packs

Fastest path while demoing: open **Packs** in the nav and click **Load demo
pack** — the app reseeds from the chosen bundled pack, shows a success
state, and every section re-skins. Use it right after showing the Reference
page: the before/after is the whole architecture argument in one click.

The command-line equivalents below still work unchanged and are what you'd
use outside the browser (scripts, containers, packs not in the bundled
allowlist).

The seed script clears existing content before loading, so switching packs
is just a reseed — the database always holds exactly one pack and two
domains can never mix.

### Default — Tidewatch Guild (celestial navigation)

```bash
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

### ArchiveGuild (historical-archive apprenticeship)

```bash
SEED_PATH=data/seed_archiveguild.json python -m backend.app.seed
SEED_PATH=data/seed_archiveguild.json uvicorn backend.app.main:app --reload
```

### CytoFISH Navigator (synthetic FISH/cytogenetics education)

```bash
SEED_PATH=data/seed_cytofish_synthetic.json python -m backend.app.seed
SEED_PATH=data/seed_cytofish_synthetic.json uvicorn backend.app.main:app --reload
```

> Note: passing `SEED_PATH` to `uvicorn` as well matters only on the very first
> request to a fresh database, when the app auto-seeds if it finds no data. If
> you seeded explicitly first (as above), the database is already populated and
> the app serves whatever is in it.

Then open <http://127.0.0.1:8000>. Confirm the banner and home page name the
pack you loaded, and check <http://127.0.0.1:8000/api/v1/pack-metadata> to see
the raw metadata.

## Demo narration (the 90-second version)

(A tighter 60-second variant lives in the README's "60-second demo script"
section; this one adds the pack-switching payoff.)

1. **Open the home page.** Point out the "Active content pack" card and the
   banner — the app tells you which domain is loaded and restates that it is
   synthetic-only.
2. **Browse Reference → an item.** Show categorized, searchable content with
   markdown bodies.
3. **Open a practice case.** Reveal steps one at a time to show the guided
   reveal, ending in the outcome.
4. **Take the quiz, submit.** Emphasize that answers are scored server-side and
   never appear in the page source.
5. **Switch packs** (reseed with a different `SEED_PATH`, restart, refresh).
   Same app, same routes, completely different domain — this is the payoff
   shot.

## Screenshots to capture for a portfolio walkthrough

Capture each at ~1280px width. To show content-agnosticism, capture the first
one for **all three packs**; the rest can use whichever pack reads best
(CytoFISH is the most impressive for a technical audience).

| File | View | What it demonstrates |
|------|------|----------------------|
| `home-tidewatch.png` | Home (`#/`) with Tidewatch loaded | Active-pack card + banner |
| `home-archiveguild.png` | Home with ArchiveGuild loaded | Same UI, different pack |
| `home-cytofish.png` | Home with CytoFISH loaded | Same UI, specialized domain |
| `reference-cytofish.png` | Categories with a search in progress | Search + taxonomy |
| `item-detail.png` | A reference item | Markdown content rendering |
| `practice-case.png` | A case with two steps revealed | Guided reveal UX |
| `training.png` | Training modules page | Module-grouped lessons |
| `quiz-cytofish-results.png` | Quiz after "Check answers" | Server-side scoring + explanations |
| `pack-metadata.png` | `/api/v1/pack-metadata` JSON, or `/docs` | Governance metadata exposed via API |

An animated GIF of switching packs (home page before/after a reseed) is the
single most convincing artifact for this project — it shows the whole
content-agnostic thesis in one loop.

## Bonus beat: scaffold a brand-new pack live

For a technical audience, showing the *authoring* story lands well — it proves
the content-agnostic thesis isn't just three prepared files but a repeatable
workflow.

```bash
# 1. Scaffold a valid, safe-by-default pack in one command.
python -m backend.app.new_pack demo_pack

# 2. It passes the validator immediately — before any content is written.
python -m backend.app.validate_pack data/seed_demo_pack.json   # -> OK

# 3. Seed it and run (seeding replaces whatever pack was loaded before).
SEED_PATH=data/seed_demo_pack.json python -m backend.app.seed
SEED_PATH=data/seed_demo_pack.json uvicorn backend.app.main:app --reload
```

Open <http://127.0.0.1:8000>: the banner and home card name the new
`Demo Pack`, and every section renders the placeholder starter records. The
narration: *"A new domain starts from a valid, governed skeleton — I only
replace the TODO records; I never rebuild the contract."* Delete the throwaway
file afterward (`rm data/seed_demo_pack.json`) so it doesn't get committed.

Full authoring workflow and schema: [CONTENT_AUTHORING.md](CONTENT_AUTHORING.md).

## Safety reminder for the CytoFISH pack

The CytoFISH pack is **synthetic educational content only**: no patient
information, no real cases, no accession numbers, no protocols, and no
diagnostic language. When demoing it, describe it as a demonstration of
conceptual reasoning and review/escalation habits — never as a clinical or
laboratory tool.

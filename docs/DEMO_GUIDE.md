# NavigatorEdu — Demo Guide

A step-by-step script for demonstrating NavigatorEdu locally, including how to
switch between the three content packs and what to capture for a portfolio
walkthrough.

Each pack is loaded by seeding the database from a different JSON file via the
`SEED_PATH` environment variable. The application code never changes — only the
content does. The home page and top banner display the **active content pack**
so it is always clear which domain is loaded.

## One-time setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Switching packs

Because the seed script upserts by primary key and the packs share an ID
scheme, always start each demo from a **fresh database** so two domains don't
mix.

### Default — Tidewatch Guild (celestial navigation)

```bash
rm -f data/navigatoredu.db
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

### ArchiveGuild (historical-archive apprenticeship)

```bash
rm -f data/navigatoredu.db
SEED_PATH=data/seed_archiveguild.json python -m backend.app.seed
SEED_PATH=data/seed_archiveguild.json uvicorn backend.app.main:app --reload
```

### CytoFISH Navigator (synthetic FISH/cytogenetics education)

```bash
rm -f data/navigatoredu.db
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
| `categories.png` | Categories with a search in progress | Search + taxonomy |
| `item-detail.png` | A reference item | Markdown content rendering |
| `practice-case.png` | A case with two steps revealed | Guided reveal UX |
| `training.png` | Training modules page | Module-grouped lessons |
| `quiz-results.png` | Quiz after "Check answers" | Server-side scoring + explanations |
| `pack-metadata.png` | `/api/v1/pack-metadata` JSON, or `/docs` | Governance metadata exposed via API |

An animated GIF of switching packs (home page before/after a reseed) is the
single most convincing artifact for this project — it shows the whole
content-agnostic thesis in one loop.

## Safety reminder for the CytoFISH pack

The CytoFISH pack is **synthetic educational content only**: no patient
information, no real cases, no accession numbers, no protocols, and no
diagnostic language. When demoing it, describe it as a demonstration of
conceptual reasoning and review/escalation habits — never as a clinical or
laboratory tool.

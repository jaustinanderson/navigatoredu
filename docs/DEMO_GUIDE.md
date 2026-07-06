# NavigatorEdu — Demo Guide

A presenter's script for demonstrating NavigatorEdu live — before an
interview, on a screen-share, or over someone's shoulder. Two paths: a
**2-minute demo** (the architecture argument and nothing else) and a
**5-minute technical demo** (the full reviewer path with narration).

Both paths align with the in-app **Reviewer guide** (`#/guide`, in the top
navigation; mirrored in [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md)) — if you're
handing the demo to someone else rather than presenting, just point them
there.

## One-time setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

Open <http://127.0.0.1:8000>. (Deployed a copy via the Render blueprint?
The demo works identically at the hosted URL.)

## Presenting a hosted demo? Smoke-check it first

Before any screen-share against a deployed URL, run the smoke check — it
takes seconds and turns "I hope the free-tier instance is awake" into a
printed checklist:

```bash
python scripts/smoke_deploy.py --base-url https://YOUR-RENDER-URL --expected-pack-id cytofish_synthetic
```

It verifies the instance is alive, serving the expected pack, declaring
its synthetic-only posture, and answering the API endpoints the demo path
uses (including a stateless quiz-report round-trip). Exit code 0 means
present with confidence; anything else tells you exactly which beat of the
demo would have failed. No local checkout handy? Run the **Hosted demo
smoke check** workflow from the repo's Actions tab instead.

## The 2-minute demo

One argument, made visually: *the entire domain is data*.

1. **Home** (15s) — "This is a learning platform. The banner and this
   manifest card tell you which content pack is loaded — right now, a
   fictional celestial-navigation domain — and that everything is
   synthetic."
2. **Reference** (20s) — "Categories, searchable items, filters. Remember
   what this content looks like."
3. **Packs → load CytoFISH → back to Reference** (45s) — "One click
   reseeded the database from a different JSON pack. Same code, same
   routes, same UI — an entirely different domain, here a synthetic
   cytogenetics education pack. Nothing about the models, API, or frontend
   encodes a domain."
4. **Close** (20s) — "The pack is validated in CI like code: structure,
   references, quiz sanity, and governance metadata including a mandatory
   synthetic-only declaration. That's the project: content held to the same
   contract discipline as code."

## The 5-minute technical demo

The 2-minute demo, plus the capabilities and the proof. Follow the same
order as the in-app Reviewer guide:

1. **Home** — point out the active-pack manifest card (served by
   `GET /api/v1/pack-metadata`) and the synthetic-only banner.
2. **Packs → load CytoFISH** — one click reseeds through the same
   clear-then-load path the CLI uses; only bundled, allowlisted packs, no
   uploads.
3. **Reference: search + filters** — type a partial word (*pro* finds
   *probe* — FTS5 prefix matching), then click a tag chip and a difficulty
   chip. Filtering is server-side; the active-filter bar and "Clear all"
   keep state obvious. Mention: the FTS index is rebuilt on every reseed,
   so pack switches can never serve stale results.
4. **A practice case** — reveal guided steps one at a time; answer material
   is deliberately absent from list endpoints and fetched on demand.
5. **Quiz → Check answers → Download report** — scoring is server-side
   (view page source: no correct answers). The report is a self-contained
   printable HTML file, generated statelessly from the submitted answers —
   point at the footer line "generated locally, not stored": scope control
   as a feature.
6. **`/docs`** — the same API, self-documenting; the frontend is just one
   consumer.
7. **Close on the tests** — 159 pytest tests with no mocks, a content
   validator gating CI, and 25 Playwright browser tests including an
   axe-core accessibility audit (serious/critical fail the build) and five
   keyboard-only journeys. "The badge is green" is a claim about the repo,
   not my laptop.

## Switching packs from the command line

The UI selector covers live demos; the CLI is the canonical path outside
the browser. Seeding clears existing content first, so the database always
holds exactly one pack:

```bash
# Default — Tidewatch Guild (celestial navigation)
python -m backend.app.seed

# ArchiveGuild (historical-archive apprenticeship)
SEED_PATH=data/seed_archiveguild.json python -m backend.app.seed

# CytoFISH Navigator (synthetic FISH/cytogenetics education)
SEED_PATH=data/seed_cytofish_synthetic.json python -m backend.app.seed
```

Restart `uvicorn` with the same `SEED_PATH` if you're relying on
first-request auto-seeding; after an explicit seed the app simply serves
whatever is in the database. Confirm the banner names the pack you loaded,
and check <http://127.0.0.1:8000/api/v1/pack-metadata> for the raw
governance metadata.

## Bonus beat: scaffold a brand-new pack live

For a technical audience, the *authoring* story proves the content-agnostic
thesis isn't three prepared files but a repeatable workflow:

```bash
# 1. Scaffold a valid, safe-by-default pack in one command.
python -m backend.app.new_pack demo_pack

# 2. It passes the validator immediately — before any content is written.
python -m backend.app.validate_pack data/seed_demo_pack.json   # -> OK

# 3. Seed it and run (seeding replaces whatever pack was loaded before).
SEED_PATH=data/seed_demo_pack.json python -m backend.app.seed
SEED_PATH=data/seed_demo_pack.json uvicorn backend.app.main:app --reload
```

The narration: *"A new domain starts from a valid, governed skeleton — I
only replace the TODO records; I never rebuild the contract."* Delete the
throwaway file afterward (`rm data/seed_demo_pack.json`). Full workflow and
schema: [CONTENT_AUTHORING.md](CONTENT_AUTHORING.md).

## Screenshots

The repository ships a curated set in [../screenshots/](../screenshots/)
with descriptions in [screenshots/README.md](../screenshots/README.md). If
you re-capture after UI changes, match that list: capture at ~1280 px
width with the CytoFISH pack loaded, and keep the file names stable so
README and docs references stay valid.

## Safety reminder for the CytoFISH pack

The CytoFISH pack is **synthetic educational content only**: no patient
information, no real cases, no accession numbers, no protocols, and no
diagnostic language. When demoing it, describe it as a demonstration of
conceptual reasoning and review/escalation habits — never as a clinical or
laboratory tool.

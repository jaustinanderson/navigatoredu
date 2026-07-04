# NavigatorEdu — Content Authoring Guide

How to create, validate, and load a new **content pack** — the self-contained
JSON file that supplies every piece of domain content in the app. The
application code is content-agnostic; a pack is the only thing you write to
stand up a new domain.

This guide covers the pack schema, the required governance metadata, the
`create → validate → seed → run` workflow, how the `new_pack` scaffolder gives
you a valid starting point, and how the whole pipeline keeps content synthetic,
safe, and governable.

## The pack in one sentence

A content pack is a single JSON file (`data/seed_<slug>.json`) containing a
governance **metadata** object plus six content collections; the validator
enforces its shape, the seed script loads it into SQLite, and the running app
serves it — with zero code changes between one domain and the next.

## Quick start: scaffold a new pack

Don't hand-copy an existing pack — you'd drag along another domain's IDs and
risk dropping a governance field. Generate a fresh, valid skeleton instead:

```bash
python -m backend.app.new_pack demo_pack
```

This writes `data/seed_demo_pack.json`: a minimal, fully-wired pack that
**passes the validator immediately** and ships with the safety defaults baked
in. From there you replace the placeholder records with your own synthetic
content.

The `slug` names both the file and the `pack_id`. It must be lowercase
letters, digits, and underscores, starting with a letter (e.g. `demo_pack`,
`archive2`, `my_domain`). Invalid slugs are rejected before anything is
written.

`new_pack` refuses to overwrite an existing pack unless you pass `--force`:

```bash
python -m backend.app.new_pack demo_pack           # refuses if the file exists
python -m backend.app.new_pack demo_pack --force   # regenerate from skeleton
```

Exit codes: `0` created, `1` refused (file exists — re-run with `--force`),
`2` bad usage or invalid slug (nothing written).

## The end-to-end workflow

```
new_pack  ─►  edit  ─►  validate_pack  ─►  seed  ─►  run
 scaffold      your      enforce the       load      serve
 a skeleton    content   contract          SQLite    the app
```

```bash
# 1. Scaffold
python -m backend.app.new_pack demo_pack

# 2. Edit data/seed_demo_pack.json — replace the TODO placeholder records.

# 3. Validate (fast, no database touched)
python -m backend.app.validate_pack data/seed_demo_pack.json

# 4. Seed your pack (seeding replaces whatever pack was loaded before)
SEED_PATH=data/seed_demo_pack.json python -m backend.app.seed

# 5. Run
SEED_PATH=data/seed_demo_pack.json uvicorn backend.app.main:app --reload
```

Then open <http://127.0.0.1:8000> and confirm the banner and home card name
your pack, and <http://127.0.0.1:8000/api/v1/pack-metadata> to see the raw
governance metadata.

> Seeding is clear-then-load: the script removes existing content before
> importing, so the database always holds exactly one pack and switching
> domains is a single reseed.

## Pack schema

A pack is a JSON object with a `metadata` object and six content collections.
Every collection is a list; every record needs the fields marked required
below (the validator checks all of them).

### `metadata` (governance object — required)

Describes the pack and asserts its safety posture. The validator requires all
eight fields, and requires `synthetic_only` to be `true`.

| Field | Required | Meaning |
|-------|----------|---------|
| `pack_id` | ✓ (non-empty) | Stable identifier; matches the file slug |
| `pack_name` | ✓ (non-empty) | Human-facing name shown in the UI |
| `pack_version` | ✓ | Content version string, e.g. `"0.1.0"` |
| `pack_description` | ✓ | One-line description of the pack |
| `domain_type` | ✓ | Short domain label, e.g. `synthetic_education` |
| `synthetic_only` | ✓ (**must be `true`**) | Governance invariant for this project |
| `intended_use` | ✓ (non-empty) | Plain-language intended use; must say educational/demo only |
| `safety_notes` | ✓ | What the pack must **not** contain or be used for |

### Content collections

| Collection | Required fields | Notes |
|------------|-----------------|-------|
| `disclaimers` | `id`, `applies_to`, `text` | Safety/synthetic notices; referenced by items |
| `categories` | `id`, `name`, `slug`, `description` | Taxonomy; optional self-`parent_id` |
| `reference_items` | `id`, `category_id`, `title`, `summary`, `body_md`, `tags`, `difficulty`, `disclaimer_id` | `tags` is a list; `body_md` is markdown |
| `training_notes` | `id`, `module`, `order`, `title`, `body_md`, `related_item_ids` | `related_item_ids` → `reference_items` |
| `practice_cases` | `id`, `category_id`, `title`, `scenario_md`, `guided_steps`, `expected_outcome_md`, `difficulty` | `guided_steps` is a list |
| `quiz_questions` | `id`, `category_id`, `question`, `options`, `correct_index`, `explanation`, `source_item_id` | `correct_index` must index into `options` |

### Referential rules the validator enforces

- IDs are unique **within** each collection.
- `reference_items.category_id` → an existing `categories.id`.
- `reference_items.disclaimer_id` → an existing `disclaimers.id`.
- `practice_cases.category_id` and `quiz_questions.category_id` → `categories.id`.
- `quiz_questions.source_item_id` → an existing `reference_items.id`.
- `training_notes.related_item_ids[*]` → existing `reference_items.id`.
- `quiz_questions.options` is non-empty and `correct_index` is in range.

The scaffolded skeleton is a minimal graph that already satisfies every one of
these rules, so you can seed and run it before writing a single word of
content — then keep it green as you edit.

## Required metadata and safety defaults

The scaffolder does not leave safety to chance. Every generated pack starts
with:

- `synthetic_only: true` — the governance invariant the validator enforces.
- `intended_use` stating **educational demonstration only** — not for
  real-world, operational, clinical, diagnostic, or decision-making use.
- `safety_notes` stating **no real records, no real cases, no real
  identifiers**, and **not for operational or clinical use**.
- A global `disclaimer` record repeating the synthetic-only statement in the
  content itself.

You are free to strengthen this language for a sensitive domain (see the
CytoFISH pack for the pattern), but you cannot weaken `synthetic_only` below
`true` without failing validation.

## Keeping content synthetic and safe

The platform hosts specialized, safety-sensitive domains by keeping every
safety boundary in the **content**, never in the application code. When
authoring:

- **Invent everything.** No real people, organizations, records, cases, or
  identifiers. If a detail could be mistaken for real data, change it.
- **State the boundary in the content.** Use `disclaimers` and the metadata
  `safety_notes` to say plainly what the pack is not for. The CytoFISH pack is
  the reference example: no PHI, no accession numbers, no protocols, no
  diagnostic or sign-out language.
- **Teach concepts and habits, not procedures.** For sensitive domains, aim at
  reasoning, review, and escalation — not operational instructions.
- **Keep `synthetic_only: true`.** It is a hard gate, not a suggestion.

## How this supports content governance

Because content outlives code and is edited by people who never open the code,
every content edit is effectively a deploy. This authoring pipeline treats a
data contract with the same rigor as a code contract:

- **Provenance and intended-use are mandatory metadata**, not optional prose.
  A pack cannot ship without declaring what it is, what it's for, and that it
  is synthetic-only.
- **The validator is the gate.** Structure, references, quiz sanity, and the
  `synthetic_only` invariant are all enforced — and CI runs the validator on
  every shipped pack on every push, so a bad content edit fails the build just
  like a code regression.
- **The scaffolder makes the safe path the easy path.** The lowest-effort way
  to start a pack is also the one that begins valid and safe-by-default, so
  authors add content on top of a green, governed baseline instead of
  reconstructing the contract by hand.
- **The active pack is queryable at runtime.** `GET /api/v1/pack-metadata`
  reports exactly what was seeded, so "which content is live, and is it cleared
  for real use?" is an enforced, inspectable fact — the same discipline behind
  dataset datasheets, model cards, and data-catalog lineage.

## Adding a pack to CI (optional)

Shipped packs are swept automatically by the test suite
(`backend/tests/test_validate_pack.py` globs `data/seed*.json`), so a new pack
committed to `data/` is validated by the tests with no edit. If you also want
the explicit CLI validation step in `.github/workflows/ci.yml` to name your
pack, add one line:

```yaml
      - name: Validate content packs
        run: |
          python -m backend.app.validate_pack data/seed.json
          python -m backend.app.validate_pack data/seed_archiveguild.json
          python -m backend.app.validate_pack data/seed_cytofish_synthetic.json
          python -m backend.app.validate_pack data/seed_demo_pack.json   # your pack
```

## Reference

- Scaffolder: `backend/app/new_pack.py`
- Validator: `backend/app/validate_pack.py`
- Seed loader: `backend/app/seed.py`
- Architecture rationale: [ARCHITECTURE.md](ARCHITECTURE.md)
- Local demo walkthrough: [DEMO_GUIDE.md](DEMO_GUIDE.md)

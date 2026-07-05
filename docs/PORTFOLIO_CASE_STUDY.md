# NavigatorEdu — Portfolio Case Study

*A professional case study of the project: what it is, why it was built this
way, and what it demonstrates. For interview preparation specifically, see
[INTERVIEW_TALKING_POINTS.md](INTERVIEW_TALKING_POINTS.md).*

## Context

NavigatorEdu is a portfolio project: a full-stack learning platform built to
be read and evaluated by employers, not shipped to users. It was developed in
nine sequential milestones, each delivered with tests, documentation, and CI
green, so the repository history itself demonstrates incremental,
disciplined delivery.

The product shape is deliberately familiar — a reference library, training
modules, guided practice cases, and a quiz engine — because that shape recurs
across real systems (LMS platforms, documentation products, onboarding
tools, laboratory training material). The interesting engineering is not the
shape; it is that the entire knowledge domain is data.

## Problem

Two problems, one demonstrated solution:

1. **Product problem.** Specialized fields need learning tools that combine
   searchable reference material, scenario-based practice, and
   self-assessment over one coherent data model.
2. **Engineering problem.** Content-driven systems usually treat content as
   an afterthought: unvalidated, unversioned, coupled to code. When content
   outlives code and is edited by people who never read the code, every
   content edit is effectively a deploy — and deserves deploy-grade rigor.

NavigatorEdu answers both: the product shape is built end-to-end, and the
content is held to a validated, governed, CI-enforced contract.

## Design constraints

Constraints were chosen up front and kept:

- **No authentication, no external APIs, no AI features.** The scope is a
  single reviewer-runnable process; every added service dilutes the signal.
- **Beginner-manageable stack.** FastAPI + SQLite + a no-build-step frontend:
  anyone can clone, seed, and run in under a minute.
- **All content synthetic.** No real organizations, people, records, or
  procedures anywhere — enforced mechanically, not just promised.
- **No overbuilding.** Every trade-off (JSON columns, linear-scan search,
  hand-rolled validation) is the honest choice at this scale, with the
  upgrade path named in the code or docs.
- **Documentation is a first-class deliverable.** README, architecture
  notes, authoring guide, demo guide, and this case study ship with the code.

## Architecture

One FastAPI process serves a static single-page frontend and a versioned
JSON REST API. SQLModel maps six content tables plus a single-row
`PackMetadata` table onto SQLite. All domain content originates in one JSON
**content pack**; an idempotent clear-then-load seed script loads the pack
selected by the `SEED_PATH` environment variable, so the database always
holds exactly one pack.

```
content pack (JSON) ─► validate_pack ─► seed.py ─► SQLite ─► FastAPI ─► SPA + /docs
        ▲
   new_pack scaffolder
```

Three complete packs ship: two fictional domains (celestial navigation,
archive apprenticeship) and one synthetic specialized domain
(cytogenetics/FISH education). Swapping packs changes every page of the
product with zero code changes — the concrete proof that the models, routes,
and frontend encode structure, not content.

Full detail and rationale: [ARCHITECTURE.md](ARCHITECTURE.md).

## Safety and synthetic-content approach

The project's safety posture has three layers, all mechanical:

1. **Content-level boundaries.** The CytoFISH pack — a safety-sensitive
   domain — contains no PHI, no real cases, no accession numbers, no
   protocols, and no diagnostic or sign-out language. Those exclusions are
   stated in the pack's own disclaimers, which are schema objects rendered in
   the product, not README promises.
2. **Governance metadata.** Every pack must declare `pack_id`, `pack_name`,
   `pack_version`, `pack_description`, `domain_type`, `intended_use`,
   `safety_notes`, and `synthetic_only: true`. The validator fails any pack
   that omits these or weakens the synthetic-only invariant, and CI runs the
   validator on every push.
3. **Safe-by-default authoring.** The `new_pack` scaffolder generates new
   packs with the safety defaults already in place, so the lowest-effort path
   to a new domain is also the governed one.

The positioning is deliberately modest: this demonstrates safe modeling of a
sensitive domain and governance instinct. It makes no claim of clinical
validity, clinical use, or clinical expertise.

## Testing and validation strategy

- **One seam, no mocks.** Every route receives its DB session via
  `Depends(get_session)`. Tests override that single dependency with an
  in-memory SQLite engine seeded from the same pack format — real queries
  end-to-end, and the development database is never touched.
- **101 tests** across API behavior (including the security-relevant
  properties: quiz answers never serialized on GET, scoring server-side),
  pack switching, validator behavior (broken-pack fixtures built by mutating
  a copy of a real pack), and the authoring command (all file I/O in temp
  directories so CI's working tree stays clean).
- **Content validated like code.** A parametrized test sweeps every
  `data/seed*.json` automatically, and CI additionally runs the validator CLI
  against each shipped pack. A content edit that breaks a reference fails the
  build exactly like a code regression.

## What changed over the milestones

| Milestone | Delivered | Tests |
|-----------|-----------|-------|
| v01 | MVP blueprint: positioning, architecture, data model, build plan | — |
| v02 | Working scaffold: FastAPI + routers, SQLite/SQLModel, upserting seed script | 14 |
| v03 | Training modules, Docker (non-root) + compose, GitHub Actions CI, full docs | 17 |
| v04 | `SEED_PATH` content-pack switching — architecture proven content-agnostic | 26 |
| v05 | Content-pack validator CLI, collect-all-errors, CI-gated | 39 |
| v06 | CytoFISH Navigator: synthetic specialized pack, safety in content | 48 |
| v07 | Per-pack governance metadata, `PackMetadata` table, metadata endpoint + UI banner | 57 |
| v08 | `new_pack` authoring scaffolder: valid, safe-by-default skeletons | 87 |
| v09 | Portfolio polish: documentation, positioning, interview preparation | 87 |
| v10 | Frontend reviewer-experience polish; clear-then-load seeding fix | 91 |
| v11 | Content Pack Browser: allowlisted local-demo pack selector | 101 |

The arc is intentional: build the product, prove the abstraction
(`SEED_PATH`), enforce the contract (validator), stress it with a hard domain
(CytoFISH), make governance explicit (metadata), then make the safe path the
easy path (authoring). Test count grew with every functional milestone.

## What this demonstrates professionally

| Skill | Where a reviewer sees it |
|-------|--------------------------|
| REST API design | Versioned prefix, list/detail response shaping, correct 400/404 usage |
| Data modeling | Seven related tables with FKs; deliberate JSON-column trade-off, documented |
| Security thinking | Quiz answers never leave the server; server-side scoring; HTML-escaped rendering |
| Testing discipline | 101 tests on isolated in-memory DBs via dependency override — no mocks |
| Data pipelines | Idempotent seed script; human-reviewable JSON as source of truth; CLI validator gating CI; scaffolder for safe-by-default authoring |
| Content governance | Required provenance/intended-use metadata, validated in CI; active pack queryable at runtime |
| Safe domain modeling | A sensitive domain hosted with every safety boundary in content and metadata, none in code |
| Documentation | README, ARCHITECTURE, CONTENT_AUTHORING, DEMO_GUIDE, this case study; OpenAPI for free |
| Operations basics | Docker (non-root, layer caching), compose volume + healthcheck, GitHub Actions CI |
| Product judgment | Reveal-as-you-go practice cases; disclaimer system built into the schema |

Two transferable ideas run through everything:

- **Content-agnostic architecture** — identifying the invariant structure
  beneath a domain and keeping it out of the code is the load-bearing idea in
  LMS platforms, white-label products, and documentation systems.
- **Data contracts with code-contract rigor** — required metadata, a gating
  validator, and CI enforcement are the same discipline behind schema
  registries, dataset datasheets, and ETL data-quality gates.

## Honest limitations

- No authentication or user state — quiz scores are per-request.
- Search is a linear scan over a small corpus (FTS5 is the named upgrade).
- Single-container deployment; CI runs tests but there is no CD.
- The frontend is intentionally minimal; it demonstrates API consumption,
  not frontend engineering depth.

Naming limitations yourself, with a rationale, is a stronger signal than
pretending they don't exist.

## Future roadmap

Kept realistic and incremental — see [ROADMAP.md](ROADMAP.md) for the full
plan (UI polish, an in-app pack selector, richer search, exportable learning
reports, a deployment option, and — only after substantially stronger
guardrails — an AI/RAG study assistant).

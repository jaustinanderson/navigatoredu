# NavigatorEdu — Portfolio Case Study

*A professional case study of the project: what it is, why it was built this
way, and what it demonstrates. For a 3–5 minute hands-on evaluation path,
see the [Reviewer Guide](REVIEWER_GUIDE.md); for interview preparation
specifically, see [INTERVIEW_TALKING_POINTS.md](INTERVIEW_TALKING_POINTS.md).*

## The 60-second version

NavigatorEdu is a full-stack learning platform — searchable reference
library, training modules, guided practice cases, server-scored quizzes —
where **the entire knowledge domain is one validated JSON file**. Load a
different file and the same codebase becomes a different product: three
complete demo domains ship in the repo, including a fully synthetic
cytogenetics/FISH education pack. Everything is covered by 159 backend
tests (no mocks), 25 real-browser tests including an accessibility audit
and keyboard-only journeys, a content validator that gates CI, a Docker
build check, a one-file deployment blueprint, and a hosted-demo smoke
check that proves a deployed instance is alive and synthetic-only. All
content is synthetic; nothing is suitable for clinical or operational
use — and that boundary is machine-enforced, not just promised.

It was built in twenty-two sequential milestones, each delivered with
tests, documentation, and CI green, so the repository history itself
demonstrates incremental, disciplined delivery.

The engineering arc, in one line per act: prove the **content-pack
architecture** (one codebase, three domains, zero code changes to switch);
give it real capabilities (**FTS5 search** with composable filters,
**exportable stateless quiz reports**, a **deployment option**); then prove
it holds up (**Playwright browser tests**, an **axe-core accessibility
audit** that fails the build on serious violations, **keyboard-only journey
tests**); and finally make it effortless to evaluate (an in-app **Reviewer
guide** with tested links, mirrored in the [Reviewer Guide](REVIEWER_GUIDE.md)
doc).

## Context

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
- **No overbuilding.** Every trade-off (JSON columns, hand-rolled
  validation, a no-build-step frontend) is the honest choice at this scale,
  with the upgrade path named in the code or docs.
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
- **159 tests** across API behavior (including the security-relevant
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
| v12 | Reviewer landing: self-guiding home page with walkthrough, scope, and safety posture | 101 |
| v13 | FTS5 search + tag/difficulty filters; index rebuilt per seed; linear scan retired | 124 |
| v14 | Exportable learning reports: stateless, printable HTML per quiz attempt | 137 |
| v15 | Deployment option: Render blueprint + CI Docker build check, no CD | 137 |
| v16 | Project retrospective: v01–v15 engineering narrative and debugging stories | 137 |
| v17 | Playwright browser tests: 12 UI-behavior tests + dedicated CI job | 137 pytest + 12 browser |
| v18 | axe-core accessibility audit in CI (fails on serious/critical); contrast fixes it forced | 137 pytest + 16 browser |
| v19 | Keyboard-only journeys: main tasks proven completable without a mouse | 137 pytest + 21 browser |
| v20 | Reviewer guide: in-app 3–5 minute evaluation walkthrough with tested CTAs | 137 pytest + 25 browser |
| v21 | Final portfolio polish: README restructure, screenshot refresh, Reviewer Guide doc | 137 pytest + 25 browser |
| v22 | Hosted-demo smoke checks: deployment verification script + manual workflow — the portfolio demo is externally verifiable | 159 pytest + 25 browser |

The arc is intentional: build the product, prove the abstraction
(`SEED_PATH`), enforce the contract (validator), stress it with a hard domain
(CytoFISH), make governance explicit (metadata), then make the safe path the
easy path (authoring) — and finally make the whole thing effortless to
*evaluate*: automated accessibility and keyboard coverage, a reviewer
guide inside the product itself, and a presentation pass so the repository
reads clearly in a reviewer's first three minutes. Test count grew with
every functional milestone.

## What this demonstrates professionally

| Skill | Where a reviewer sees it |
|-------|--------------------------|
| REST API design | Versioned prefix, list/detail response shaping, correct 400/404 usage |
| Data modeling | Seven related tables with FKs; deliberate JSON-column trade-off, documented |
| Security thinking | Quiz answers never leave the server; server-side scoring; HTML-escaped rendering |
| Testing discipline | 159 tests on isolated in-memory DBs via dependency override — no mocks |
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

## The retrospective

This case study describes the destination; [RETROSPECTIVE.md](RETROSPECTIVE.md)
describes the journey — a milestone-by-milestone narrative including the
three substantial bugs (stale-seed pack drift, the chip-rendering CSS
failure, and version-drift/packaging discipline), how each was diagnosed,
and how the fixes changed the architecture. For a reviewer, it is the more
revealing document: features show what was built, but debugging stories
show how the builder thinks when the plan stops working.

## Honest limitations

- No authentication or user state — quiz scores are per-request; the
  learner keeps results via the stateless downloadable report, by design.
- Search is unranked-beyond-bm25 FTS5 over small synthetic packs — real demo
  search, not production search infrastructure (no tuning, no highlighting).
- Single-container deployment with a deploy-it-yourself Render blueprint;
  CI proves the image builds, but there is deliberately no CD — a portfolio
  demo warrants a build check, not a pipeline.
- The frontend is intentionally minimal; it demonstrates API consumption,
  not frontend engineering depth — though as of v17 its behavior is guarded
  by a real-browser Playwright suite, born directly from the chip-rendering
  incident.

Naming limitations yourself, with a rationale, is a stronger signal than
pretending they don't exist.

## Status and future work

As of v22 the project is a **complete portfolio demo**: every planned
milestone shipped, closing with presentation polish (v21) and hosted-demo
smoke checks (v22) — so the demo is not just runnable but *externally
verifiable*: anyone can point `scripts/smoke_deploy.py` (or the manual
GitHub Actions workflow) at a deployed URL and get a pass/fail checklist
proving it is alive, serving the expected pack, and synthetic-only.
[ROADMAP.md](ROADMAP.md) records the full shipped arc and a short
list of possible future work (richer authoring tooling, a maintained hosted
demo, typed API client generation, and — only after substantially stronger
guardrails — an AI/RAG study assistant).

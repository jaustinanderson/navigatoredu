# NavigatorEdu — Portfolio Case Study

*How to present this project on GitHub, LinkedIn, a résumé, and in interviews.*

## One-line summary

> Full-stack reference and training platform (FastAPI, SQLModel/SQLite,
> vanilla-JS SPA) with a searchable content library, training modules,
> guided practice cases, and a server-scored quiz engine — fully tested and containerized.

## The problem it demonstrates solving

Specialized fields need structured learning tools: reference material,
scenario practice, and self-assessment, tied together by a coherent data
model. This project builds that product shape end-to-end using a fictional
domain, so the engineering is evaluable without any proprietary or sensitive
content.

Choosing a **fictional domain is a feature, not a dodge**: it proves the
architecture is domain-agnostic. And the repo now proves it concretely: two
complete content packs (celestial navigation and archive apprenticeship)
drive the same code, switched by one environment variable. This is the
difference between *claiming* separation of content and structure and
*demonstrating* it — a reviewer can run both products from one codebase in
under a minute.

Why this matters beyond the demo: content-agnostic design is the load-bearing
idea in real product families (LMS platforms, documentation systems,
white-label apps). Showing you can identify the invariant structure beneath
a domain — and keep it out of your code — is an architecture skill, not a
content trick.

### Specialization without coupling

The third pack, **CytoFISH Navigator**, is the strongest form of this
argument. It is a *specialized, safety-sensitive* domain — synthetic
cytogenetics/FISH education — yet it required **zero code changes**: same
models, same routes, same validator, same frontend. The domain knowledge
lives in content; the engineering stays generic.

It also demonstrates handling a domain where *what you leave out* matters as
much as what you include. Every safety boundary — no PHI, no real cases, no
accession numbers, no protocols, no diagnostic or sign-out language — is
enforced in the content and stated in the pack's own disclaimers, not bolted
onto the code. For any employer in health, legal, finance, or another
regulated space, that instinct — put the domain's safety rules where the
domain lives, and keep the platform neutral — is exactly the judgment they're
screening for.

## Skills evidenced, mapped to the code

| Skill | Where a reviewer sees it |
|-------|--------------------------|
| REST API design | Versioned prefix, list/detail response shaping, correct 400/404 usage |
| Data modeling | Six related entities with FKs; deliberate JSON-column trade-off, documented |
| Security thinking | Quiz answers never leave the server; server-side scoring; HTML-escaped rendering |
| Testing discipline | 26 tests on isolated in-memory DBs via dependency override — no mocks |
| Data pipelines | Idempotent seed script; human-reviewable JSON as source of truth; CLI validator gating CI |
| Documentation | README, ARCHITECTURE.md, DEMO_GUIDE.md, this case study; OpenAPI for free |
| Content governance | Required per-pack metadata, validated in CI; active pack surfaced in API + UI |
| Operations basics | Docker (non-root user, layer caching), compose volume + healthcheck, GitHub Actions CI |
| Product judgment | Reveal-as-you-go practice cases; disclaimer system built into the schema |

## Talking points for interviews

1. **"Walk me through your testing strategy."** One dependency —
   `get_session` — is the seam. Tests override it with an in-memory SQLite
   engine seeded from the same JSON as production. Real queries run; nothing
   is mocked; the dev database is never touched.
2. **"What trade-offs did you make?"** JSON columns instead of join tables
   for list fields; in-Python text matching instead of FTS5; a no-build-step
   frontend. Each is the right call at this scale, and each has a named,
   documented upgrade path.
3. **"How would you scale it?"** Postgres via a connection-string change,
   FTS or an external index for search, a real frontend build if the UI
   grows. The point: the current design doesn't block any of these.
4. **"Why can't users cheat the quiz?"** `GET /quiz` strips answers before
   serialization; grading happens in `POST /quiz/submit`. Verified by a
   dedicated test.

## Suggested résumé bullet

> Designed and built a full-stack learning platform (Python/FastAPI, SQLite,
> REST) featuring structured reference content, scenario-based practice, and
> a server-scored quiz engine; 100% of endpoints covered by an isolated
> pytest suite; containerized with Docker.

## Suggested LinkedIn post skeleton

- What it is (1–2 sentences), with a screenshot or GIF.
- One interesting decision (the quiz-answer isolation is the most relatable).
- What you learned; link to the repo.
- Explicit note that all content is fictional/synthetic — this reads as
  professionalism, not weakness.

## Future expansion ideas

- **Quiz attempt history** — first feature that would justify user state.
- **FTS5 search** — the documented upgrade path once content grows.
- **Content authoring CLI** — validate/lint `seed.json` before import;
  demonstrates pipeline thinking.
- ~~**Second fictional domain**~~ — shipped: the ArchiveGuild pack proves
  content-agnosticism (one new JSON file, zero code changes).
- ~~**Pack validation tooling**~~ — shipped: `validate_pack` runs in CI, so
  the pack format is now an enforced interface.
- ~~**Domain specialization**~~ — shipped: the CytoFISH pack proves a
  specialized, safety-sensitive domain fits the generic architecture unchanged.
- **Pack scaffolding** — a `new_pack` generator emitting a valid skeleton
  would complete the authoring toolchain.

## Why metadata + governance matter here

The metadata milestone turns "which content is loaded?" from tribal knowledge
into an enforced, queryable fact. Every pack must declare `pack_id`,
`pack_name`, `intended_use`, and affirm `synthetic_only: true`, or the
validator fails the build. The active pack is then exposed via
`GET /api/v1/pack-metadata` and shown in the UI banner.

Why an interviewer should care: in real informatics and content-driven
systems, *provenance and intended-use labelling* are governance requirements,
not niceties. Knowing — at runtime, from the system itself — exactly which
content set is live, what it is for, and whether it is cleared for real use is
the same discipline behind dataset datasheets, model cards, and data-catalog
lineage. Encoding "this is synthetic, this is its intended use" into the
content contract and enforcing it in CI is a small, concrete demonstration of
that instinct.

## Why validation matters here

In any reusable education or informatics system, content outlives code and
is edited by people who never read the code. Every content edit is then a
deploy — and unvalidated content fails at the worst possible time: at import,
or silently at runtime (a quiz whose `correct_index` points past its options
is a bug users find for you).

The validator moves those failures to the earliest possible moment, with
errors written for content authors ("quiz_questions 'q-003': correct_index 7
out of range for 4 options"), and CI runs it on every push. The transferable
skill on display: treating data contracts with the same rigor as code
contracts. This is the same discipline behind schema registries, API
contract tests, and ETL data-quality gates in production systems.

## Honest limitations (know these before an interviewer finds them)

- No authentication or user state — quiz scores are per-request.
- Search is linear scan over a small corpus.
- Single-container deployment; CI runs tests but there is no CD.
- Frontend is intentionally minimal; it demonstrates API consumption, not
  frontend engineering depth.

Naming limitations yourself, with a rationale, is a stronger signal than
pretending they don't exist.

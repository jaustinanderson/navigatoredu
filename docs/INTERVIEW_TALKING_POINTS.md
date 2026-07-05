# NavigatorEdu — Interview Talking Points

Concise preparation for discussing this project in interviews. Everything
here is accurate to the repo — no claim in this document outruns what the
code and tests actually show.

## The 30-second version

> "NavigatorEdu is a full-stack learning platform I built where the entire
> knowledge domain is data: a validated JSON content pack loaded into SQLite.
> One FastAPI codebase hosts three complete demo domains — including a fully
> synthetic cytogenetics/FISH education pack — switched by a single
> environment variable. It has 124 tests with no mocks, a CI-gated content
> validator, and governance metadata so the system itself reports what
> content is loaded and that it's synthetic-only."

## The 2-minute version

> "The product shape is familiar: a reference library, training modules,
> guided practice cases, and a server-scored quiz. The interesting part is
> that none of the content lives in code. Everything comes from a JSON
> content pack — one file — loaded by an idempotent seed script into SQLite,
> selected by an environment variable. I shipped three packs: two fictional
> domains, and a synthetic cytogenetics/FISH education pack, and switching
> between them re-skins the entire product with zero code changes. That's the
> core claim of the architecture, and it's demonstrated rather than asserted.
>
> Because content is the product, I treated the content format as a real
> contract. There's a CLI validator that checks structure, foreign
> references, quiz sanity, and required governance metadata — every pack must
> declare its ID, version, intended use, and affirm it's synthetic-only, or
> CI fails. There's also a scaffolding command that generates a new pack
> that's valid and safe-by-default from the first second, so the easiest way
> to start a new domain is also the governed one.
>
> Testing runs through one dependency-injection seam: every route gets its
> database session through a single dependency, and tests override just that
> with an in-memory SQLite engine. So it's 124 tests running real queries, no
> mocks, and the dev database is never touched. CI runs the suite plus the
> validator on every push.
>
> I kept the scope deliberately tight — no auth, no external services, a
> no-build-step frontend — so a reviewer can clone it and have it running in
> under a minute, and so every trade-off I did make has a documented upgrade
> path."

## Ten talking points

1. **Content-agnostic architecture, proven not claimed.** Three complete
   domains run on one codebase; switching is one environment variable. This
   is the load-bearing idea behind LMS platforms and white-label products.
2. **Data contracts with code-contract rigor.** The pack format is enforced
   by a validator that runs in CI — a content edit that breaks a reference
   fails the build exactly like a code regression.
3. **One test seam, zero mocks.** Overriding a single `get_session`
   dependency points 124 tests at an isolated in-memory database running real
   queries. Small surface, high confidence.
4. **Server-side quiz integrity.** `GET /quiz` strips answers before
   serialization; grading happens in `POST /quiz/submit`. A dedicated test
   verifies answers never reach the client.
5. **Safe modeling of a sensitive domain.** The CytoFISH pack contains no
   PHI, no real cases, no accession numbers, no protocols, no diagnostic
   language — and those boundaries live in the content and its metadata, not
   bolted onto code.
6. **Governance as a queryable fact.** `GET /api/v1/pack-metadata` reports
   exactly what was seeded — provenance and intended-use labelling in the
   same spirit as dataset datasheets and model cards.
7. **Make the safe path the easy path.** The `new_pack` scaffolder emits a
   pack that is valid and safe-by-default before the author types a word —
   the same instinct as secure-by-default templates and paved-path tooling.
8. **Idempotent data pipeline.** The seed script clears content tables and
   loads only the selected pack, so re-seeding converges and switching
   domains is a single reseed; content is human-reviewable JSON, diff-able
   in a PR.
9. **Deliberate, documented trade-offs.** JSON columns over join tables,
   hand-rolled validation, no-build frontend — each is
   the honest choice at this scale, each has a named upgrade path.
10. **Incremental delivery discipline.** Nine milestones, each shipped with
    tests and docs and green CI; test count grew from 14 to 87 across them.
    The commit history is itself evidence.

## Five likely questions, with strong answers

**1. "Walk me through your testing strategy."**
> "Every route receives its database session through one FastAPI dependency,
> `get_session`. That's the seam: the test suite overrides just that
> dependency with an in-memory SQLite engine seeded from the same content
> format production uses. So the tests run the real query code end-to-end —
> nothing is mocked — and the development database is never touched. On top
> of that, content is tested like code: a parametrized test sweeps every
> shipped pack through the validator, and broken-pack test fixtures are built
> by mutating a copy of the real pack, so they stay valid as content evolves."

**2. "What trade-offs did you make, and why?"**
> "Four main ones, all documented in the repo with their upgrade paths. JSON
> columns instead of join tables for list-valued fields — simpler and still
> queryable at this scale. Search started as a linear scan and was upgraded
> to SQLite FTS5 in v13 once the feature justified it — shipping the named
> upgrade path on schedule is itself the point. Hand-rolled validation instead
> of JSON Schema — at six collections it reads clearer and produces
> friendlier errors for content authors. And a no-build-step frontend — it
> keeps the run story to one command and puts the emphasis on the backend and
> data design, which is where I wanted the signal."

**3. "How would you scale this?"**
> "Postgres is a connection-string change — SQLModel abstracts the rest and
> the JSON columns work on both. Search is already on SQLite FTS5, rebuilt
> per seed; the next step there would be an external index if the corpus
> outgrew one process. User state starts with a `QuizAttempt` table persisting
> submissions, which adds progress tracking without touching existing routes.
> The important point is that the current design blocks none of these — the
> trade-offs were chosen to be reversible."

**4. "Why did you use synthetic content instead of a real domain?"**
> "Two reasons. Practically, it means the engineering can be evaluated
> without any proprietary or sensitive content in the repo. But more
> importantly, it's the point of the architecture: a fictional domain proves
> the code encodes structure, not content. And for the cytogenetics pack
> specifically, synthetic-only is the responsible way to model a
> safety-sensitive domain — it let me demonstrate familiarity with the shape
> of that content while enforcing, mechanically, that nothing real and
> nothing clinical is in there. The validator literally fails any pack that
> doesn't affirm `synthetic_only: true`."

**5. "What would you do differently if you started over?"**
> "I'd introduce the validator earlier — it landed at milestone five, and
> once it existed, every content change got cheaper and safer; that's the
> tool I'd want from day one. I'd also design the governance metadata into
> the pack format from the start instead of retrofitting it at milestone
> seven. The general lesson I took: for content-driven systems, the content
> contract *is* the architecture, so invest in enforcing it first."

## Explaining the clinical-lab / informatics relevance — without overclaiming

The honest framing, in one paragraph:

> "The CytoFISH pack is an education-shaped model of a cytogenetics domain —
> panels, probes, signal-pattern reasoning, review and escalation habits —
> built entirely from synthetic content. It demonstrates two things relevant
> to laboratory informatics: that I understand the *shape* of structured
> content in that field, and that I have the governance instincts the field
> requires — knowing what to leave out, stating intended use explicitly, and
> enforcing those boundaries mechanically rather than by promise. It is not a
> clinical tool, it isn't validated for any real use, and I don't present it
> as clinical experience — I present it as evidence of how I'd handle
> content, provenance, and safety discipline in a regulated environment."

Things **not** to say (they overclaim and an interviewer will notice):

- Anything implying the pack could support real interpretation, training for
  clinical duties, or laboratory workflows.
- "Medical-grade," "clinically accurate," or "validated" in any real-world
  sense — the only validation here is the structural/governance validator.
- That the project demonstrates domain *expertise*. It demonstrates domain
  *interest* plus transferable engineering and governance discipline; let
  credentials and lab experience speak for expertise.

## Suggested résumé bullet

> Designed and built a full-stack learning platform (Python/FastAPI, SQLite,
> REST) with a content-pack architecture hosting three swappable demo
> domains; enforced content contracts via a CI-gated validator and governance
> metadata; 87-test pytest suite on isolated databases with no mocks;
> containerized with Docker.

## If asked "what is this project, really?"

A fair, modest summary: a portfolio project, deliberately scoped, whose value
is the discipline it demonstrates — separation of structure and content,
enforced data contracts, real-query testing, safety-by-default tooling, and
documentation treated as a deliverable. It is small on purpose, and every
limitation is named in the case study before an interviewer can find it.

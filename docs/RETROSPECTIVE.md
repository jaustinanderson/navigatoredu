# NavigatorEdu — Project Retrospective

*The project as an engineering story: how the architecture evolved across
fifteen milestones, what broke along the way, how each problem was
diagnosed, and what the incidents taught. Written for reviewers who want to
see judgment, not just features.*

## 1. Executive summary

NavigatorEdu is a synthetic educational content-pack platform: a FastAPI +
SQLite backend and a static single-file frontend, where the **entire
knowledge domain lives in one validated JSON content pack**. The same
codebase serves three complete demo domains — celestial navigation, archive
apprenticeship, and a cytogenetics/FISH education pack — switched by a
single environment variable or one click in the UI. Nothing about the
models, routes, or frontend encodes a domain; they encode structure, and
the packs supply everything else.

Every record in every pack is fictional and synthetic. There is no PHI, no
real patient data, no clinical use, and the system enforces that posture
mechanically: each pack must declare `synthetic_only: true` in governance
metadata that a validator checks in CI on every push. This is a
portfolio/education demo, and it says so on every surface it has.

The build was deliberately incremental: fifteen milestones, each delivered
with tests and documentation, test count growing from 14 to 137, CI green
throughout. The interesting parts of this document are the places where
that discipline was tested — three substantial bugs, each of which changed
how the system works.

## 2. Milestone-by-milestone narrative

**v01 — Blueprint.** Positioning, architecture, data model, and build plan
before any code. This fixed the constraints that held for the whole
project: no auth, no external services, beginner-manageable stack,
everything synthetic, documentation as a first-class deliverable. Deciding
what *not* to build first is why the later milestones compose instead of
sprawl.

**v02 — Working scaffold.** FastAPI with three routers, SQLite via
SQLModel, a seed script, and the first 14 tests — including the decision
that defined the testing story: every route takes its session from one
`Depends(get_session)`, and tests override only that, running real queries
against isolated in-memory databases. No mocks then, no mocks now.

**v03 — Training modules, Docker, CI, docs.** The project became
continuously provable: a non-root Dockerfile, compose with a persistent
volume and healthcheck, GitHub Actions running the suite on every push, and
the README/ARCHITECTURE/case-study trio. From here on, "done" meant "green
in CI with docs updated," which is the habit the rest of the story leans on.

**v04 — `SEED_PATH` pack switching.** The architectural thesis, proven: a
second complete domain (ArchiveGuild) loaded by pointing one environment
variable at a different JSON file, zero code changes. This milestone turned
"content-agnostic" from a claim into a demonstration — and created the
capability every later feature builds on.

**v05 — Content-pack validator.** If content is the product, the content
format is a contract, so it got contract enforcement: a CLI validator
checking structure, required fields, unique IDs, referential integrity, and
quiz sanity — collecting *all* errors before reporting, and wired into CI.
A broken content edit now fails the build exactly like a code regression.

**v06 — CytoFISH Navigator.** The stress test: a safety-sensitive domain
(cytogenetics/FISH education) modeled entirely with synthetic content — no
PHI, no real cases, no accession numbers, no protocols, no diagnostic
language — with every boundary carried in the pack's own disclaimers rather
than bolted onto code. This is the pack that connects the project to
laboratory-informatics work while proving the discipline the field demands.

**v07 — Pack governance metadata.** Every pack must now declare what it is
and what it's for: id, name, version, domain type, intended use, safety
notes, and `synthetic_only: true`, validated in CI, stored at seed time in
a single-row table, and served by `GET /api/v1/pack-metadata`. "Which
content is live, and is it cleared for real use?" became an enforced,
queryable fact — the same instinct as dataset datasheets and model cards.

**v08 — Authoring workflow.** `python -m backend.app.new_pack <slug>` emits
a minimal, fully-wired pack that passes the validator immediately and
ships safe-by-default. The safe path became the easy path: authors start
from a green, governed baseline instead of hand-copying another domain's
file and hoping they didn't drop a governance field.

**v09 — Portfolio documentation polish.** The repo learned to explain
itself: README rewritten for a 30-second skim, the case study restructured,
interview talking points and a realistic roadmap added. Positioning is part
of a portfolio project's engineering, not an afterthought.

**v10 — Frontend reviewer experience (and the first big bug).** The UI got
its design system — manifest card, walkthrough, real loading/empty/error
states, accessibility basics. Manual review then surfaced the **stale-seed
bug** (story A below), whose fix changed seeding semantics for good:
clear-then-load, so the database always holds exactly one pack.

**v11 — Content Pack Browser.** Pack switching moved into the UI behind a
hard-coded allowlist: `GET /packs` lists the bundled packs (metadata read
live from the pack files), `POST /packs/select` reseeds through the same
`seed()` the CLI uses. Deliberately not an upload or admin feature — the
boundaries (no paths, no scanning, nothing reflected in errors) are the
point.

**v12 — Reviewer landing.** The home page became self-guiding: hero, the
60-second walkthrough with a "notice this" line per step, what-this-
demonstrates, what's intentionally out of scope, tech stack. A reviewer now
gets positioning, safety posture, and demo path without opening a doc.

**v13 — FTS5 search and filters (and the second big bug).** Search moved
from linear scan to SQLite FTS5 — the upgrade path named in the code since
v02 — with the index rebuilt as the final step of every seed, making stale
cross-pack search results structurally impossible. Tag and difficulty
filters landed in the API and UI. The filter chips then produced the
**chip-rendering bug** (story B below), which took two fixes and ended by
removing a whole class of failure.

**v14 — Exportable learning reports.** After checking a quiz, a learner can
download a self-contained, printable HTML report — generated statelessly
from the submitted answers, nothing stored, every dynamic value escaped
(with an adversarial test injecting script payloads into every field). The
no-accounts constraint held by making the learner the keeper of their own
artifact.

**v15 — Deployment option.** A Render blueprint (free tier, browser-only
deploy from a fork, consuming the existing Dockerfile with a PORT-aware
CMD), `SEED_PATH` documented for pack selection at deploy time, and a CI
`docker-build` job that builds and smoke-tests the image on every push — a
build check, deliberately not CD.

## 3. Bugs and debugging stories

### A. The stale-seed / pack-drift bug

**Symptom.** Running the CytoFISH pack, the home banner correctly said
*CytoFISH Navigator* — but the Reference page still showed categories from
Tidewatch and ArchiveGuild. The app was announcing one domain and serving
three.

**Root cause.** The seed script upserted via `session.merge()`, and each
pack uses its own ID scheme (`cat-instruments` vs `cat-panel-foundations`).
Seeding pack B over pack A inserted B's rows and never touched A's — while
the governance metadata, being a single fixed-ID row, flipped correctly.
The metadata and the content could disagree, which is the worst failure
mode for a system whose selling point is governance. The docs had said
"switch on a fresh database," which made this a documented footgun rather
than no footgun.

**Fix.** Seeding became **clear-then-load**: delete all content tables
child-first, then insert only the selected pack. The database now always
holds exactly one pack — the one the metadata names — and re-seeding stays
idempotent. Four regression tests pin it, including one that walks the
exact reported scenario.

**Why it compounded well.** Clear-then-load quietly made seeding the single
content-write path, and everything later leaned on that: the v11 pack
browser is safe because `POST /packs/select` calls the same `seed()`; the
v13 FTS index can be rebuilt-from-scratch at the end of every seed and can
therefore *never* drift from the active pack — no triggers, no incremental
bookkeeping. One bug fix became the invariant two later features stood on.

**Lesson.** When state can be derived, derive it from one controlled
transition rather than patching it incrementally. And treat "the docs say
don't do that" as a bug report about the design.

### B. The chip-rendering bug

**Symptom.** The v13 tag-filter chips sometimes rendered as blank pill
outlines; the label appeared only on hover or after clicking. Item-card
tag pills were fine; difficulty chips were fine; the data was fine.

**First hypothesis, ruled out.** Bad data (empty/duplicate/quote-bearing
tags) — an audit of all three packs found none. Second hypothesis: class-
toggle logic. Real: the selection code added `text-white` without removing
`text-slate-600`, leaving two same-property utilities on one element with
stylesheet order deciding the winner. A fix made the toggle sets provably
disjoint, verified programmatically… and the browser still showed blank
chips.

**Actual root cause.** The remaining variable was the one a headless
harness can't see: the **Tailwind Play CDN generates utility CSS at
runtime** for dynamically-injected DOM, via a MutationObserver, and both
the presence and relative order of same-property utility rules in that
generated stylesheet are outside the page's control. Chip readability
depended on runtime-generated CSS behaving favorably for `innerHTML`-
injected content — a dependency that is fragile by construction and
unverifiable from a test harness.

**Final fix.** Remove the dependency instead of adjusting it: a static
`.facet-chip` CSS component in the document `<head>` — present before any
JS runs — explicitly setting color, background, border, opacity, font
metrics, and display for every state, with selection keyed off
`aria-pressed="true"` (which the code was already maintaining for
accessibility). `paint()` shrank to setting one attribute; chips carry no
utility classes at all. Verification moved closer to the browser too: a
real-DOM audit asserting *computed* styles at rest, selected, and after
deselection, across all three packs.

**Lesson.** When a provably-correct fix doesn't change the observed
behavior, the bug is in a layer you're not observing — so either observe
that layer or remove it. For state-dependent UI, a few lines of explicit
CSS beat clever utility interplay; and accessibility state
(`aria-pressed`) making a great styling hook is a sign the two belong
together.

### C. Version drift and packaging discipline

**Symptom class.** Fifteen milestones delivered as versioned ZIPs, several
with mid-milestone fixes (`v10_ui_polish_fix`, two v13 UI fixes), and a
roadmap whose planned version numbers drifted from reality (planned-v12
search shipped as v13; planned-v13 reports shipped as v14). The standing
risk: building on a stale base, shipping an artifact that doesn't match
the tree, or documentation that silently disagrees with the code.

**The checkpoint system that emerged.** Every milestone starts from a
fresh `git clone` of the pushed repo — never a local tree — so the base is
exactly what GitHub holds. `git status --short` before packaging shows
precisely what the milestone touched. Every ZIP gets a unique
milestone-named file and matching top-level folder, then is **extracted
fresh and re-verified** — full test suite, validators, and the milestone's
end-to-end checks run against the artifact itself, not the working tree.
Doc consistency is enforced by grep sweeps for stale claims (test counts,
retired behaviors like "linear scan" or "switch on a fresh database")
whenever semantics change. And CI re-proves the suite on push, so the repo
can't quietly diverge from the last green state. Where numbering drifted,
the roadmap says so explicitly rather than being rewritten to look
prescient.

**Lesson.** Reproducibility is a workflow property, not a tool: fresh
base, explicit diff, uniquely named artifact, verify the artifact itself,
and let CI arbitrate. Honest drift notes beat retconned plans.

### D. (Small, but instructive) The test that was wrong

While testing the v14 report's HTML escaping, an assertion failed because
real pack text contains apostrophes, which `html.escape(quote=True)`
renders as `&#x27;` — the raw string genuinely isn't in the document. The
code was right; the test's expectation was wrong. The fix was to compare
escaped forms, and to add an adversarial test injecting script payloads
into every dynamic field so the property being protected — no live markup
survives — is asserted directly rather than by proxy. Lesson: when a test
fails, "which side is wrong?" is a real question; fixing the test is
legitimate only when you can name the property the code correctly upholds.

## 4. Architecture lessons learned

- **Content packs as data, not hardcoded pages.** Identifying the invariant
  structure beneath a domain and keeping it out of the code is what made
  three domains, an authoring tool, and a pack browser cheap. The moment of
  proof is always the same: swap the pack, watch every page change.
- **Validation before seeding.** A gate at the data boundary converts
  content mistakes from runtime surprises into build failures — the same
  reason code gets type checks and tests.
- **Seed/reseed as a controlled state transition.** Clear-then-load means
  the database is always a pure function of one pack file. Every stale-state
  bug class died with that decision.
- **The FTS index as derived state.** Rebuild-from-source at each
  transition is simpler and safer than incremental maintenance at this
  scale; correctness by construction beats correctness by bookkeeping.
- **Stateless report generation.** The report is computed from the request
  and thrown away. No accounts, no tables, no retention — the strongest
  privacy stance is having nothing to protect.
- **No accounts/persistence as scope control.** Every excluded feature was
  excluded for a reason a reviewer can read; the honest "intentionally out
  of scope" list is a feature.
- **CI as proof, not decoration.** Tests, validators, and now a Docker
  build+smoke run on every push; "the badge is green" is a claim about the
  repo, not about the developer's laptop.
- **Docker build as deployment confidence.** The image building and
  answering requests from a clean checkout is what makes the Render
  blueprint a one-click truth rather than an aspiration.

## 5. What I would improve next

- **Frontend test automation.** The Node render harness and jsdom
  computed-style audits caught a lot, but the chip bug proved some failures
  live only in a real browser. **Playwright** tests for chip rendering,
  filter interaction, and the report download would close that gap.
- **Richer authoring tooling.** `new_pack` scaffolds; a `--seed`
  smoke-check flag and a pack linting/preview mode would shorten the
  author's loop further.
- **Optional hosted demo.** The blueprint exists; maintaining one live URL
  (with an uptime badge) would remove the last click for reviewers.
- **Accessibility testing.** Manual keyboard/contrast checks should become
  automated axe-core runs in CI.
- **Typed API client generation from OpenAPI.** The frontend hand-codes
  fetch calls; generating a typed client would demonstrate schema-driven
  integration and catch response-shape drift.
- **Clearer engine/content separation.** The platform engine and the demo
  packs share one repo for reviewability; splitting them (engine as a
  package, packs as content repos) is the natural next structural step if
  this grew beyond a portfolio piece.

## 6. Interview-ready takeaways

**"Tell me about the project."**
- A learning platform where the whole domain is a validated JSON content
  pack; three synthetic domains run on one codebase, switched by one
  variable or one click. 137 tests, no mocks; validator and Docker build in
  CI; stateless exportable reports; deploy blueprint included.

**"Tell me about a bug you fixed."**
- Stale-seed: metadata said CytoFISH, Reference showed three domains —
  upsert-by-merge left old packs' rows behind. Fix: clear-then-load
  seeding, which became the invariant the pack browser and FTS rebuilds
  later relied on.
- Chip rendering: blank filter chips that survived a provably-correct
  class-logic fix — root cause was runtime-generated utility CSS ordering.
  Fix: a static CSS component keyed off `aria-pressed`, removing the
  fragile layer entirely.

**"How did you prevent regressions?"**
- One DI seam, real queries, isolated DBs; every bug fix lands with tests
  that walk the exact reported scenario; content validated like code in CI;
  artifacts extracted fresh and re-verified before shipping.

**"How did you think about safety?"**
- Synthetic-only enforced mechanically (validator + CI), boundaries carried
  in the content and its governance metadata, allowlist-only pack loading,
  server-side quiz scoring, escaped report output with adversarial tests,
  and statelessness so there's nothing to breach.

**"What tradeoffs did you make?"**
- SQLite over Postgres, JSON columns over join tables, hand-rolled
  validation over JSON Schema, no-build frontend over a framework — each
  the honest choice at this scale, each documented with its upgrade path,
  and one (linear scan → FTS5) actually exercised on schedule.

## 7. Safety posture

All content in this project is synthetic and fictional. There is no PHI,
no real patient data, no real cases or identifiers, and no diagnostic or
sign-out language anywhere in any pack — the CytoFISH pack models the
*shape* of a sensitive domain while excluding everything that would make it
operationally usable. This is not clinical software and is not validated
for any real-world, operational, or clinical use; it is a
portfolio/education demonstration, and that statement is enforced by the
system itself (`synthetic_only: true`, checked in CI), displayed in the UI,
embedded in every exported report, and repeated here.

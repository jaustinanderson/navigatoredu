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

## Skills evidenced, mapped to the code

| Skill | Where a reviewer sees it |
|-------|--------------------------|
| REST API design | Versioned prefix, list/detail response shaping, correct 400/404 usage |
| Data modeling | Six related entities with FKs; deliberate JSON-column trade-off, documented |
| Security thinking | Quiz answers never leave the server; server-side scoring; HTML-escaped rendering |
| Testing discipline | 26 tests on isolated in-memory DBs via dependency override — no mocks |
| Data pipelines | Idempotent seed script; human-reviewable JSON as source of truth |
| Documentation | README, ARCHITECTURE.md, this case study; OpenAPI for free |
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
- **Third-party pack tooling** — a JSON-schema validator for packs would
  turn "content pack" into a real, documented interface.

## Honest limitations (know these before an interviewer finds them)

- No authentication or user state — quiz scores are per-request.
- Search is linear scan over a small corpus.
- Single-container deployment; CI runs tests but there is no CD.
- Frontend is intentionally minimal; it demonstrates API consumption, not
  frontend engineering depth.

Naming limitations yourself, with a rationale, is a stronger signal than
pretending they don't exist.

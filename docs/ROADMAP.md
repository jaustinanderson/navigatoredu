# NavigatorEdu — Roadmap

Realistic, incremental next milestones. Each keeps the project's constraints:
beginner-manageable, reviewer-runnable in one command, all content synthetic,
tests and docs shipped with every change. Versions continue the existing
milestone sequence (v09 was portfolio polish).

## v10 — UI polish

Tighten the frontend without adding a build step: consistent spacing and
typography, loading and empty states, small-screen layout fixes, keyboard
navigation for the quiz, and clearer active-pack presentation. Success
criterion: the screenshots checklist can be re-captured and every view looks
deliberate.

## ~~v11 — Content-pack browser / demo selector~~ (shipped)

Shipped as the Content Pack Browser: `GET /api/v1/packs` lists the three
bundled packs from a hard-coded allowlist (metadata read live from each
pack file), `POST /api/v1/packs/select` reseeds the local demo database
through the same clear-then-load path the CLI uses, and a Packs page in the
frontend shows the manifest of each pack with a Load button. Deliberately
not shipped: filesystem scanning, uploads, or user-supplied paths — the
selector is a local-demo convenience, not an admin surface.

## ~~Richer search and filtering~~ (shipped in v13)

Shipped: free-text search moved from linear scan to SQLite FTS5 (the upgrade
path named in the code since v02), with the index rebuilt on every seed so
pack switches can never serve stale results; `?tag=` and `?difficulty=`
filters on the items endpoint, surfaced as chips in the Reference UI with an
active-filter bar and Clear. The linear-scan path is fully retired (one
documented fallback: a never-seeded database returns no matches rather than
erroring). Actual version numbers drifted from this plan: v12 became the
reviewer landing polish, so search landed as v13.

## ~~Exportable learning reports~~ (shipped in v14)

Shipped: `POST /api/v1/quiz/report` returns a self-contained, printable
HTML report (score, per-question submitted/correct answers, explanations,
related reference titles, pack governance metadata, synthetic-only footer),
with a Download button on the quiz results. Generated statelessly from the
submitted answers in the request — no accounts, no persistence, no new
tables — keeping the no-auth constraint intact. PDF was skipped
deliberately: it would add a heavy dependency for no reviewer value
(browsers print HTML). Version drift again: planned as v13, shipped as v14.

## ~~Frontend browser tests~~ (shipped in v17)

Shipped: a 12-test Playwright suite (`tests/browser/`) targeting the exact
failure classes manual review previously caught — chip readability asserted
on computed styles, filter behavior, pack-switch staleness through the real
UI, and the report download verified file-in-hand — with a self-starting
web server config and a dedicated `browser-test` CI job. This was the top
item on the retrospective's improvement list.

## ~~Project retrospective~~ (shipped in v16)

Shipped: [RETROSPECTIVE.md](RETROSPECTIVE.md) — the v01–v15 engineering
narrative with the three major debugging stories and architecture lessons,
plus refreshed interview bug stories. A documentation milestone by design:
no app behavior changed, all 137 tests untouched and passing.

## ~~Deployment option~~ (shipped in v15)

Shipped: a Render blueprint (`render.yaml`, free tier, browser-only deploy
from a fork, consuming the existing Dockerfile with a PORT-aware CMD),
`SEED_PATH` documented for choosing the bundled pack at deploy time, a
"Live demo / deployment" README section, and a CI `docker-build` job that
builds and smoke-tests the image on every push — a build check, not CD
(`autoDeploy: false`). The repo explains exactly how a live URL comes to
exist; hosting one is the reader's single click. Version drift continues:
planned as v14, shipped as v15.

## Later — AI/RAG study assistant (only after stronger guardrails)

An assistant that answers questions strictly from the loaded pack's content
is the obvious eventual feature — and deliberately not next. Prerequisites
before it would be responsible to build:

- Retrieval strictly scoped to pack content, with citations to the source
  records, and refusal behavior when the answer isn't in the pack.
- Guardrails that inherit the pack's governance metadata: the assistant must
  surface `synthetic_only` and `intended_use`, and must not present CytoFISH
  content as clinical guidance under any phrasing.
- An evaluation harness (adversarial prompts included) checked into the repo
  and run in CI, so the safety claims are tested, not asserted.
- A cost/complexity story consistent with the project: no external service
  can become required just to run the demo.

Until all of that exists, the project's answer to "why no AI features?" is a
feature, not a gap: it reflects the same judgment the rest of the repo
demonstrates — don't ship what you can't validate.

## Explicit non-goals

- Authentication and user accounts (until a feature genuinely requires
  persistent user state).
- Real (non-synthetic) content of any kind, in any pack.
- Microservices, message queues, or a frontend build pipeline at this scale.

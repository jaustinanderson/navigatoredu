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

## v11 — Content-pack browser / demo selector

An in-app way to see which packs exist and switch between them for demos.
Likely shape: a read-only endpoint listing the packs found in `data/`
(reusing the validator to badge each as valid/invalid), plus a small demo
page. Actual switching still happens by reseeding — the selector documents
and launches that honestly rather than pretending to hot-swap; hot
switching would require per-pack databases or namespacing and is out of
scope until something needs it.

## v12 — Richer search and filtering

Move free-text search from linear scan to SQLite FTS5 (the upgrade path
named in the code since v02), add tag and difficulty filters to the items
endpoint, and surface them in the UI. Success criterion: search behavior is
covered by tests and the linear-scan code path is fully retired.

## v13 — Exportable learning reports

A per-session summary a learner could keep: quiz results with explanations
and linked reference items, exportable as printable HTML (PDF only if it
stays dependency-light). Still no accounts — the report is generated from
the submitted answers in the request, keeping the no-auth constraint intact.

## v14 — Deployment option

One documented, low-cost deployment target (a container platform such as
Fly.io or Render), with the compose setup adapted, environment variables
documented, and a deploy section in the README. CI gains a build check but
not full CD. Success criterion: a reviewer can visit a live URL, and the
repo explains exactly how it got there.

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

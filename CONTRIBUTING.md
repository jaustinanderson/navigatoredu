# Contributing to NavigatorEdu

NavigatorEdu is a content-driven learning-platform portfolio project. Contributions should preserve its central architectural claim: domain content is supplied by validated, swappable content packs while the application code encodes reusable structure.

## Before Making a Change

- Read the README, architecture documentation, reviewer guide, and retrospective.
- Keep all bundled content fictional and synthetic.
- Do not add PHI, real patient information, employer-confidential material, internal procedures, or proprietary clinical-system content.
- Preserve the explicit boundary that the CytoFISH pack is educational and not suitable for clinical or operational use.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1`.

Run the main validation and test commands before opening a pull request:

```bash
python -m backend.app.validate_pack data/seed.json
python -m backend.app.validate_pack data/seed_archiveguild.json
python -m backend.app.validate_pack data/seed_cytofish_synthetic.json
python -m pytest -q
```

Install the locked Node development dependencies and Playwright browser before
running the browser and accessibility layer:

```bash
npm ci
npx playwright install --with-deps chromium
npm run test:browser
```

## Change Workflow

1. Create a focused branch from `main`.
2. Make the smallest coherent change.
3. Update tests for behavior changes.
4. Validate every affected content pack.
5. Run backend, browser, accessibility, and Docker checks that apply to the change.
6. Update reviewer-facing documentation when visible behavior or architecture changes.
7. Open a pull request with verification evidence and safety confirmation.

## Content-Pack Rules

A pack must:

- Pass the content validator
- Declare `synthetic_only: true`
- Include governance and intended-use metadata
- Use internally consistent IDs and references
- Avoid real organizations, people, patients, cases, or operational procedures
- Keep answer material out of list endpoints and other unintended surfaces
- Remain compatible with the generic platform without domain-specific code branches

Do not weaken the validator merely to make an invalid pack pass. Correct the content or explicitly evolve the contract with tests and documentation.

## Application Rules

- Keep API response shapes deliberate and versioned.
- Preserve server-side scoring and answer-protection boundaries.
- Escape or sanitize user-visible content appropriately.
- Keep the local pack selector allowlisted; do not add arbitrary filesystem paths or uploads.
- Preserve the non-root Docker runtime and health check.
- Avoid adding authentication or persistence without a separately reviewed threat model and product requirement.

## Pull-Request Expectations

State:

- What changed and why
- Which backend, frontend, content-pack, deployment, or documentation areas changed
- Test, validation, browser, accessibility, and Docker results
- Whether the hosted-demo behavior changed
- Confirmation that all content remains synthetic
- Any limitations or deferred work

## Scope Control

Large changes such as accounts, arbitrary uploads, multi-tenant persistence, production authentication, real clinical content, or a framework rewrite require a separate proposal. They should not be bundled into maintenance or unrelated feature work.

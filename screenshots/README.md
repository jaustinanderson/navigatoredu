# Screenshots

Captured views of the final product (v21). All application shots show the
**CytoFISH Navigator synthetic pack** active — the most representative
domain for a technical audience — at 1280 px viewport width, 2× scale.

## Files

- `home-cytofish-pack.png` — home page: hero, reviewer walkthrough entry
  points, and the active-pack manifest card (governance metadata, intended
  use, synthetic-only badge)
- `reviewer-guide.png` — the in-app **Reviewer guide** (`#/guide`, full
  page): the 3–5 minute evaluation path with tested CTA links
- `reference-search-filters.png` — Reference page with an FTS5 search
  (`probe`) plus tag and difficulty filter chips active, showing the
  active-filter bar and server-side narrowing
- `training-cytofish.png` — training modules grouped by concept, with
  related-reference links
- `practice-case-reveal-cytofish.png` — a synthetic practice case with
  guided steps revealed one at a time
- `quiz-report-download.png` — quiz results after **Check answers**:
  server-side score, per-question explanations, and the **Download report**
  button (stateless printable HTML)
- `packs-browser.png` — the Packs page (full page): all three bundled,
  allowlisted packs with their governance metadata and the active pack
  marked
- `api-pack-metadata.png` — Swagger UI (`/docs`) with the
  `GET /api/v1/pack-metadata` endpoint expanded
- `accessibility-browser-tests.png` — Playwright HTML report of a local run
  of the accessibility (axe-core), keyboard-journey, Reviewer-guide, chip,
  and filter/pack-switching suites: 23/23 passing (the two remaining
  browser tests — quiz report download and the API-docs smoke — run in the
  same CI `browser-test` job)

## Notes

All screenshots use synthetic educational demo content only.

The content-pack browser is a local portfolio/demo feature. It only loads
bundled, allowlisted demo packs and does not accept arbitrary user-uploaded
files or filesystem paths.

Capture environment note: these were captured in a sandbox whose network
policy blocks the Tailwind/Google-Fonts/jsdelivr CDNs, so the identical
assets (the same Tailwind theme compiled locally, the same Source Serif 4
font from `@fontsource`, `swagger-ui-dist` from npm) were substituted at
capture time. The application code was not modified.

// Automated accessibility audit (axe-core via @axe-core/playwright).
//
// Scope and honesty notes:
//   - Each of the four user-facing views (Home, Reference, Packs, Quiz) is
//     rendered in a real browser and scanned with the full default axe-core
//     ruleset (WCAG 2.x A/AA + best practices). No rules are disabled and
//     no elements are excluded from the scan.
//   - The FAILURE threshold is impact >= serious (axe impacts: minor,
//     moderate, serious, critical). Minor/moderate findings do not fail CI,
//     but they are PRINTED in the test output so they stay visible instead
//     of silently ignored. Rationale: serious/critical map to defects that
//     block or badly degrade assistive-technology use; the lower tiers are
//     tracked as advisory until triaged.
//   - Automated scanning is necessary but not sufficient: axe catches
//     roughly the mechanically checkable subset (names, roles, contrast,
//     landmarks, ARIA validity). Keyboard-only task flows and screen-reader
//     UX still need a human pass — see docs/ARCHITECTURE.md.
//
// The scans run against a deterministic pack (Tidewatch, selected through
// the app's real endpoint) so contrast/content findings are reproducible.
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const { selectPack } = require('./helpers');

const FAILING_IMPACTS = ['serious', 'critical'];

function formatViolations(violations) {
  return violations
    .map((v) => {
      const nodes = v.nodes
        .slice(0, 5)
        .map((n) => `      ${n.target.join(' ')}\n        ${n.failureSummary.replace(/\n/g, '\n        ')}`)
        .join('\n');
      const more = v.nodes.length > 5 ? `\n      …and ${v.nodes.length - 5} more node(s)` : '';
      return `  [${v.impact}] ${v.id}: ${v.help}\n    ${v.helpUrl}\n${nodes}${more}`;
    })
    .join('\n\n');
}

async function auditCurrentPage(page, label) {
  const results = await new AxeBuilder({ page }).analyze();

  const failing = results.violations.filter((v) => FAILING_IMPACTS.includes(v.impact));
  const advisory = results.violations.filter((v) => !FAILING_IMPACTS.includes(v.impact));

  if (advisory.length) {
    // Visible but non-fatal: keeps minor/moderate findings on the radar.
    console.log(`\n[a11y advisory] ${label} — ${advisory.length} non-blocking finding(s):\n${formatViolations(advisory)}\n`);
  }

  expect(
    failing,
    `Accessibility violations (serious/critical) on ${label}:\n\n${formatViolations(failing)}\n`
  ).toEqual([]);
}

test.describe('Accessibility audit (axe-core, fails on serious/critical)', () => {
  test('Home has no serious or critical violations', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/');
    await page.waitForSelector('#app h1');
    await auditCurrentPage(page, 'Home (#/)');
  });

  test('Reference has no serious or critical violations', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/categories');
    // Wait for the async facet chips + category sections to render, so the
    // scan sees the page users actually interact with.
    await page.waitForSelector('button.facet-chip');
    await page.waitForSelector('[data-cat-section]');
    await auditCurrentPage(page, 'Reference (#/categories)');
  });

  test('Packs has no serious or critical violations', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/packs');
    // Pack cards render after the packs fetch resolves.
    await page.waitForSelector('#app section');
    await auditCurrentPage(page, 'Content packs (#/packs)');
  });

  test('Quiz has no serious or critical violations', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/quiz');
    await page.waitForSelector('fieldset[data-qid]');
    await auditCurrentPage(page, 'Quiz (#/quiz)');
  });
});

// Reviewer guide (v20): the page whose entire job is being evaluable in
// 3–5 minutes. These tests pin the promises that page makes — it's
// reachable from the nav, its walkthrough and CTA links actually exist and
// point where they claim, and a keyboard user can take it up on a CTA.
// (Its axe scan lives with the other page scans in accessibility.spec.js.)
const { test, expect } = require('@playwright/test');
const { selectPack, tabTo, keyboardNavTo } = require('./helpers');

const REPO = 'https://github.com/jaustinanderson/navigatoredu';

test.describe('Reviewer guide', () => {

  test('is reachable from the top navigation', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/');
    await page.locator('nav a[data-nav="guide"]').click();
    await expect(page.locator('#app h1')).toHaveText('Reviewer guide');
    expect(page.url()).toContain('#/guide');
    // The nav marks it active like every other section.
    await expect(page.locator('nav a[data-nav="guide"]')).toHaveAttribute('aria-current', 'page');
  });

  test('carries the walkthrough structure and every promised CTA link', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/guide');
    await expect(page.locator('#app h1')).toHaveText('Reviewer guide');

    // The four walkthrough sections, as real semantic headings.
    for (const heading of ['What this is', 'What to try first', 'Technical details to notice', 'Safety boundaries', 'Jump straight in']) {
      await expect(page.locator('#app h2', { hasText: heading })).toBeVisible();
    }
    // Safety boundaries name the actual constraints.
    const safety = page.locator('section[aria-labelledby="guide-safety"]');
    for (const t of ['Synthetic content only', 'No PHI', 'No accounts', 'No persistence of quiz submissions', 'No clinical interpretation']) {
      await expect(safety).toContainText(t);
    }

    // Every CTA exists and points where it claims.
    const expectCta = async (name, href) => {
      const card = page.locator(`section[aria-labelledby="guide-jump"] a[aria-label="${name}"]`);
      await expect(card, `CTA "${name}" missing`).toBeVisible();
      await expect(card).toHaveAttribute('href', href);
    };
    await expectCta('Reference', '#/categories');
    await expectCta('Practice cases', '#/cases');
    await expectCta('Quiz', '#/quiz');
    await expectCta('Packs', '#/packs');
    await expectCta('API docs', '/docs');
    await expectCta('Portfolio case study', `${REPO}/blob/main/docs/PORTFOLIO_CASE_STUDY.md`);
    await expectCta('Retrospective', `${REPO}/blob/main/docs/RETROSPECTIVE.md`);
  });

  test('keyboard-only: reach the guide from the nav, then activate a CTA', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/');
    await page.waitForSelector('#app h1');

    // Tab to the nav item, Enter, land on the guide.
    await keyboardNavTo(page, 'guide', /^Reviewer guide$/);

    // Tab down to the Quiz CTA card and take it. The card is an <a>, so
    // this also proves the CTAs are native links, not click-handler divs.
    await tabTo(page, 'section[aria-labelledby="guide-jump"] a[aria-label="Quiz"]', { max: 60 });
    await page.keyboard.press('Enter');
    await expect(page.locator('#app h1')).toHaveText('Quiz');
    expect(page.url()).toContain('#/quiz');
  });
});

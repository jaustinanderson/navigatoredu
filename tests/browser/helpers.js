// Shared helpers for the browser tests.
const { expect } = require('@playwright/test');

// Select a bundled pack through the app's real endpoint, then land on a page.
// Uses the same allowlisted POST the Packs UI uses, so state changes travel
// the production path; the dedicated pack-switching spec also exercises the
// UI button itself.
async function selectPack(page, slug, hash = '#/categories') {
  const res = await page.request.post('/api/v1/packs/select', {
    data: { slug },
  });
  expect(res.ok()).toBeTruthy();
  await page.goto('/' + hash);
  await page.waitForSelector('#app h1');
}

// Assert a chip is genuinely readable: non-empty visible text, and a text
// color that is not the background color (the exact past failure: chips
// whose label only appeared on hover because same-property utility rules
// fought each other).
async function expectChipReadable(chip) {
  await expect(chip).toBeVisible();
  const text = (await chip.textContent()).trim();
  expect(text.length).toBeGreaterThan(0);
  const { color, backgroundColor, opacity } = await chip.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { color: cs.color, backgroundColor: cs.backgroundColor, opacity: cs.opacity };
  });
  expect(opacity).toBe('1');
  expect(color).not.toBe(backgroundColor);
  return { text, color, backgroundColor };
}

module.exports = { selectPack, expectChipReadable };

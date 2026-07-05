// Reference filter behavior (spec 2) and the pack-switching stale-category
// regression (spec 3) — the browser-level counterpart of the v10 stale-seed
// bug's backend regression tests.
const { test, expect } = require('@playwright/test');
const { selectPack } = require('./helpers');

const results = (page) => page.locator('#search-results a');

test.describe('CytoFISH Reference filters', () => {
  test.beforeEach(async ({ page }) => {
    await selectPack(page, 'cytofish');
  });

  test('searching "probe" returns CytoFISH results', async ({ page }) => {
    await page.fill('#search', 'probe');
    await expect(results(page).first()).toBeVisible();
    const count = await results(page).count();
    expect(count).toBeGreaterThan(0);
    await expect(page.locator('#search-results')).toContainText(/probe/i);
  });

  test('tag filter narrows results', async ({ page }) => {
    await page.fill('#search', 'the');           // broad query
    await expect(results(page).first()).toBeVisible();
    const before = await results(page).count();
    const chip = page.locator('button.facet-chip[data-tag]').first();
    const tag = await chip.getAttribute('data-tag');
    await chip.click();
    await expect(page.locator('#active-filters')).toContainText(`tag: ${tag}`);
    await page.waitForTimeout(300);              // debounce + refetch
    const after = await results(page).count();
    expect(after).toBeLessThanOrEqual(before);
    // every visible result carries the tag pill
    for (let i = 0; i < after; i++) {
      await expect(results(page).nth(i)).toContainText(tag);
    }
  });

  test('difficulty filter narrows results and combined filters work', async ({ page }) => {
    await page.locator('button.facet-chip[data-difficulty="beginner"]').click();
    await expect(results(page).first()).toBeVisible();
    const diffOnly = await results(page).count();
    expect(diffOnly).toBeGreaterThan(0);

    // combine with a search term: result set can only shrink
    await page.fill('#search', 'probe');
    await page.waitForTimeout(300);
    const combined = await results(page).count();
    expect(combined).toBeLessThanOrEqual(diffOnly);
    await expect(page.locator('#active-filters'))
      .toContainText('difficulty: beginner');
    await expect(page.locator('#active-filters')).toContainText('search:');
  });

  test('Clear all restores the unfiltered browse view', async ({ page }) => {
    await page.fill('#search', 'probe');
    await page.locator('button.facet-chip[data-difficulty]').first().click();
    await expect(results(page).first()).toBeVisible();
    await page.locator('#clear-filters').click();
    await expect(page.locator('#search-results')).toBeEmpty();
    await expect(page.locator('#search')).toHaveValue('');
    // category browse sections are visible again
    await expect(page.locator('[data-cat-section]').first()).toBeVisible();
  });
});

test.describe('Pack switching leaves no stale content', () => {
  test('Tidewatch -> CytoFISH via the Packs UI, verified on Reference', async ({ page }) => {
    // Start on Tidewatch through the real UI button.
    await page.goto('/#/packs');
    const tidewatchCard = page.locator('section', { hasText: 'Tidewatch' }).first();
    const loadBtn = tidewatchCard.getByRole('button', { name: /load.*demo pack/i });
    if (await loadBtn.count()) {          // absent if Tidewatch already active
      await loadBtn.click();
      await expect(page.locator('#app')).toContainText('Loaded');
    }

    await page.goto('/#/categories');
    await expect(page.locator('#app')).toContainText('Instruments');
    await expect(page.locator('#app')).not.toContainText('Panel Foundations');

    await page.fill('#search', 'astrolabe');
    await expect(results(page).first()).toBeVisible();
    await page.fill('#search', 'probe');
    await expect(page.locator('#search-results')).toContainText(/no items match/i);

    // Switch to CytoFISH through the UI.
    await page.goto('/#/packs');
    const cytoCard = page.locator('section', { hasText: 'CytoFISH' }).first();
    await cytoCard.getByRole('button', { name: /load.*demo pack/i }).click();
    await expect(page.locator('#app')).toContainText('Loaded');

    await page.goto('/#/categories');
    await expect(page.locator('#app')).toContainText('Panel Foundations');
    // Old Tidewatch categories are gone.
    await expect(page.locator('#app')).not.toContainText('Instruments');
    await expect(page.locator('#app')).not.toContainText('Sky References');

    await page.fill('#search', 'probe');
    await expect(results(page).first()).toBeVisible();
    await page.fill('#search', 'astrolabe');
    await expect(page.locator('#search-results')).toContainText(/no items match/i);
  });
});

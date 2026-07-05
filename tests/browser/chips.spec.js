// Reference chip visibility — the regression suite for the v13 chip bug,
// where tag chips rendered blank at rest. Assertions target the invariant
// (readable label: WCAG contrast >= 4.5, correct light/dark background
// family) rather than exact RGB values, and they poll past the chips'
// 150ms color transition — both lessons from this suite's own first CI run,
// which sampled mid-transition frames and failed on exact-color equality.
const { test, expect } = require('@playwright/test');
const { selectPack, expectChipReadable } = require('./helpers');

test.describe('CytoFISH Reference chips', () => {
  test.beforeEach(async ({ page }) => {
    await selectPack(page, 'cytofish');
  });

  test('tag chips are visible and readable at rest — no blank pills', async ({ page }) => {
    const tagChips = page.locator('button.facet-chip[data-tag]');
    const count = await tagChips.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const snap = await expectChipReadable(tagChips.nth(i), { background: 'light' });
      expect(snap.text.length).toBeGreaterThan(0);
    }
  });

  test('difficulty chips are visible and readable at rest', async ({ page }) => {
    const diffChips = page.locator('button.facet-chip[data-difficulty]');
    const count = await diffChips.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      await expectChipReadable(diffChips.nth(i), { background: 'light' });
    }
  });

  test('a selected tag chip stays readable on a dark background', async ({ page }) => {
    const chip = page.locator('button.facet-chip[data-tag]').first();
    await chip.click();
    await expect(chip).toHaveAttribute('aria-pressed', 'true');
    // Dark selected background, readable text — no exact-white requirement.
    await expectChipReadable(chip, { background: 'dark' });
  });

  test('a selected difficulty chip stays readable on a dark background', async ({ page }) => {
    const chip = page.locator('button.facet-chip[data-difficulty]').first();
    await chip.click();
    await expect(chip).toHaveAttribute('aria-pressed', 'true');
    await expectChipReadable(chip, { background: 'dark' });
  });

  test('Clear all resets selected filters and chips return to rest style', async ({ page }) => {
    await page.locator('button.facet-chip[data-tag]').first().click();
    await page.locator('button.facet-chip[data-difficulty]').first().click();
    await expect(page.locator('#active-filters')).toContainText('Active filters');
    await page.locator('#clear-filters').click();
    await expect(page.locator('#active-filters')).toBeEmpty();
    await expect(page.locator('button.facet-chip[aria-pressed="true"]')).toHaveCount(0);
    // Back to a readable light rest state (polled past the transition).
    await expectChipReadable(
      page.locator('button.facet-chip[data-tag]').first(),
      { background: 'light' }
    );
  });
});

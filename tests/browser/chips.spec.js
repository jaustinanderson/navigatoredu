// Reference chip visibility — the regression suite for the v13 chip bug,
// where tag chips rendered blank at rest and became readable only on
// hover/click. These assertions run against real computed styles in a real
// browser, which is exactly the layer the earlier harnesses couldn't see.
const { test, expect } = require('@playwright/test');
const { selectPack, expectChipReadable } = require('./helpers');

const SLATE = 'rgb(71, 85, 105)';   // .facet-chip at rest
const WHITE = 'rgb(255, 255, 255)';
const DEEP = 'rgb(18, 49, 79)';     // .facet-chip[aria-pressed="true"]

test.describe('CytoFISH Reference chips', () => {
  test.beforeEach(async ({ page }) => {
    await selectPack(page, 'cytofish');
  });

  test('tag chips are visible and readable at rest — no blank pills', async ({ page }) => {
    const tagChips = page.locator('button.facet-chip[data-tag]');
    const count = await tagChips.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const { color, backgroundColor } = await expectChipReadable(tagChips.nth(i));
      expect(color).toBe(SLATE);
      expect(backgroundColor).toBe(WHITE);
    }
  });

  test('difficulty chips are visible and readable at rest', async ({ page }) => {
    const diffChips = page.locator('button.facet-chip[data-difficulty]');
    const count = await diffChips.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const { color } = await expectChipReadable(diffChips.nth(i));
      expect(color).toBe(SLATE);
    }
  });

  test('a selected tag chip stays readable (white on deep navy)', async ({ page }) => {
    const chip = page.locator('button.facet-chip[data-tag]').first();
    await chip.click();
    await expect(chip).toHaveAttribute('aria-pressed', 'true');
    const { color, backgroundColor } = await expectChipReadable(chip);
    expect(color).toBe(WHITE);
    expect(backgroundColor).toBe(DEEP);
  });

  test('a selected difficulty chip stays readable', async ({ page }) => {
    const chip = page.locator('button.facet-chip[data-difficulty]').first();
    await chip.click();
    await expect(chip).toHaveAttribute('aria-pressed', 'true');
    const { color, backgroundColor } = await expectChipReadable(chip);
    expect(color).toBe(WHITE);
    expect(backgroundColor).toBe(DEEP);
  });

  test('Clear all resets selected filters and chips return to rest style', async ({ page }) => {
    await page.locator('button.facet-chip[data-tag]').first().click();
    await page.locator('button.facet-chip[data-difficulty]').first().click();
    await expect(page.locator('#active-filters')).toContainText('Active filters');
    await page.locator('#clear-filters').click();
    await expect(page.locator('#active-filters')).toBeEmpty();
    await expect(page.locator('button.facet-chip[aria-pressed="true"]')).toHaveCount(0);
    const { color } = await expectChipReadable(
      page.locator('button.facet-chip[data-tag]').first()
    );
    expect(color).toBe(SLATE);
  });
});

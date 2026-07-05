// Keyboard-only browser journeys — the complement to the axe scans.
//
// axe proves the mechanically checkable properties (names, roles, contrast,
// landmarks); these tests prove the thing axe can't: that a person using
// only a keyboard can actually COMPLETE the app's main tasks — navigate,
// search, filter, switch packs, take the quiz, download the report — and
// can see where their focus is while doing it.
//
// Ground rules for this file:
//   - No .click() and no mouse APIs in the journeys themselves. Every
//     interaction is Tab / Shift+Tab / Enter / Space through Playwright's
//     real keyboard events. The ONE exception is test setup: selecting the
//     starting pack goes through the API (page.request), exactly like the
//     rest of the suite, because arranging server state is not part of the
//     journey under test.
//   - Reaching an element is asserted by TABBING TO IT (bounded), never by
//     element.focus() — programmatic focus would prove nothing about
//     keyboard reachability, and a bounded tab count catches focus traps.
//   - Focus visibility is asserted as the invariant (a real outline appears
//     on keyboard focus and is absent when unfocused), not as exact colors.
const fs = require('fs');
const { test, expect } = require('@playwright/test');
const { selectPack } = require('./helpers');

const MAX_TABS = 40; // generous upper bound; a trap or unreachable control fails loudly

// Press Tab (or Shift+Tab) until document.activeElement matches `selector`.
// Returns the number of presses. Throws after MAX_TABS with a description of
// where focus ended up, so failures explain themselves.
async function tabTo(page, selector, { shift = false, max = MAX_TABS } = {}) {
  for (let i = 1; i <= max; i++) {
    await page.keyboard.press(shift ? 'Shift+Tab' : 'Tab');
    const hit = await page.evaluate(
      (sel) => document.activeElement && document.activeElement.matches(sel),
      selector
    );
    if (hit) return i;
  }
  const at = await page.evaluate(() => {
    const el = document.activeElement;
    return el ? `${el.tagName}${el.id ? '#' + el.id : ''} "${(el.textContent || el.value || '').trim().slice(0, 40)}"` : 'null';
  });
  throw new Error(`Could not reach ${selector} within ${max} ${shift ? 'Shift+' : ''}Tab presses; focus is on ${at}`);
}

// Keyboard-navigate to a top-nav destination from wherever focus currently
// is: Tab to the nav link, press Enter, wait for the destination heading.
async function keyboardNavTo(page, navName, headingRe) {
  await tabTo(page, `nav a[data-nav="${navName}"]`);
  await page.keyboard.press('Enter');
  await expect(page.locator('#app h1')).toHaveText(headingRe);
}

test.describe('Keyboard-only journeys', () => {

  test('1. nav smoke: every main section is reachable and activatable by keyboard', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/');
    await page.waitForSelector('#app h1');

    // Forward reachability + Shift+Tab actually moves focus backwards:
    // reach the Quiz link, step back, and land on the Training link.
    await tabTo(page, 'nav a[data-nav="quiz"]');
    await tabTo(page, 'nav a[data-nav="training"]', { shift: true, max: 1 });

    // Activate each destination with Enter and assert the page changed.
    await keyboardNavTo(page, 'categories', /^Reference$/);
    expect(page.url()).toContain('#/categories');
    await keyboardNavTo(page, 'cases', /^Practice cases$/);
    await keyboardNavTo(page, 'training', /^Training modules$/);
    await keyboardNavTo(page, 'quiz', /^Quiz$/);
    await keyboardNavTo(page, 'packs', /^Content packs$/);
  });

  test('2. Reference: search, filter by tag and difficulty, and clear — keyboard only', async ({ page }) => {
    await selectPack(page, 'cytofish', '#/');
    await page.waitForSelector('#app h1');
    await keyboardNavTo(page, 'categories', /^Reference$/);

    // Search via keyboard.
    await tabTo(page, '#search');
    await page.keyboard.type('probe');
    const results = page.locator('#search-results a');
    await expect(results.first()).toBeVisible();
    const unfiltered = await results.count();
    expect(unfiltered).toBeGreaterThan(0);

    // Tag chip, activated with Space (tag chips sit after the difficulty
    // group in tab order, so this also walks through it without activating).
    await tabTo(page, 'button.facet-chip[data-tag]');
    const tag = await page.evaluate(() => document.activeElement.getAttribute('data-tag'));
    await page.keyboard.press('Space');
    await expect(page.locator('#active-filters')).toContainText(`tag: ${tag}`);

    // Difficulty chip is BEFORE the tag group in the DOM, so reaching it
    // from here exercises Shift+Tab as a real navigation tool, and Enter as
    // the second activation key.
    await tabTo(page, 'button.facet-chip[data-difficulty]', { shift: true });
    const diff = await page.evaluate(() => document.activeElement.getAttribute('data-difficulty'));
    await page.keyboard.press('Enter');
    await expect(page.locator('#active-filters')).toContainText(`difficulty: ${diff}`);

    // Both filters registered on the chips themselves, and results narrowed.
    await expect(page.locator('button.facet-chip[aria-pressed="true"]')).toHaveCount(2);
    await expect.poll(async () => results.count()).toBeLessThanOrEqual(unfiltered);

    // Clear all, keyboard only.
    await tabTo(page, '#clear-filters');
    await page.keyboard.press('Enter');
    await expect(page.locator('#active-filters')).toBeEmpty();
    await expect(page.locator('#search')).toHaveValue('');
    await expect(page.locator('button.facet-chip[aria-pressed="true"]')).toHaveCount(0);
    await expect(page.locator('[data-cat-section]').first()).toBeVisible();
  });

  test('3. Packs: load a different pack and verify Reference reflects it — keyboard only', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/');
    await page.waitForSelector('#app h1');
    await keyboardNavTo(page, 'packs', /^Content packs$/);

    // Tab to the CytoFISH Load button (a non-active pack) and press Enter.
    await tabTo(page, 'button[aria-label^="Load the CytoFISH"]');
    await page.keyboard.press('Enter');
    await expect(page.locator('#app')).toContainText('Loaded', { timeout: 15_000 });

    // The pack load re-renders the page (focus returns to the document), so
    // getting back to Reference from scratch is itself part of the journey.
    await keyboardNavTo(page, 'categories', /^Reference$/);
    await expect(page.locator('#app')).toContainText('Panel Foundations');
    await expect(page.locator('#app')).not.toContainText('Instruments');
    await expect(page.locator('#app')).not.toContainText('Sky References');
  });

  test('4. Quiz: answer everything, check, and download the report — keyboard only', async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/');
    await page.waitForSelector('#app h1');
    await keyboardNavTo(page, 'quiz', /^Quiz$/);

    const fieldsets = page.locator('fieldset[data-qid]');
    const total = await fieldsets.count();
    expect(total).toBeGreaterThan(0);

    // Answer every question: Tab lands on the first radio of each unchecked
    // group (checked groups are skipped past by native radio-group tab
    // semantics); Space selects it. Bounded so a focus trap fails the test.
    let answered = 0;
    for (let presses = 0; answered < total && presses < MAX_TABS; presses++) {
      await page.keyboard.press('Tab');
      const onUnansweredRadio = await page.evaluate(() => {
        const el = document.activeElement;
        return !!(el && el.matches('fieldset[data-qid] input[type=radio]') &&
                  !document.querySelector(`input[name="${el.name}"]:checked`));
      });
      if (onUnansweredRadio) {
        await page.keyboard.press('Space');
        answered++;
      }
    }
    expect(answered).toBe(total);
    await expect(page.locator('fieldset[data-qid] input[type=radio]:checked')).toHaveCount(total);

    // Check answers.
    await tabTo(page, '#quiz-submit');
    await page.keyboard.press('Enter');
    await expect(page.locator('#quiz-score')).toHaveText(/Score: \d+ \/ \d+/);

    // Download the report (button only exists after checking).
    await tabTo(page, '#quiz-report-slot button', { shift: true }); // slot sits just after the submit row
    const downloadPromise = page.waitForEvent('download');
    await page.keyboard.press('Enter');
    const download = await downloadPromise;
    const html = fs.readFileSync(await download.path(), 'utf-8');
    expect(html.length).toBeGreaterThan(0);
    expect(html).toContain('Quiz Learning Report');
    expect(html).toContain('Generated locally from submitted answers; not stored.');
    expect(html).not.toContain('<script');
  });

  test('5. focus visibility: keyboard focus produces a real, measurable indicator', async ({ page }) => {
    await selectPack(page, 'cytofish', '#/categories');
    await page.waitForSelector('button.facet-chip');

    const outlineOf = (sel) =>
      page.evaluate((s) => {
        const el = document.querySelector(s);
        const cs = getComputedStyle(el);
        return {
          focused: document.activeElement === el,
          style: cs.outlineStyle,
          width: parseFloat(cs.outlineWidth) || 0,
        };
      }, sel);

    // The invariant, per control type: unfocused → no outline; keyboard
    // focus → a solid outline of measurable width. Polled, never exact-RGB.
    for (const sel of ['nav a[data-nav="categories"]', '#search', 'button.facet-chip[data-tag]']) {
      const before = await outlineOf(sel);
      expect(before.focused, `${sel} unexpectedly focused before tabbing`).toBe(false);
      // Note: Chromium reports a computed outline-width (3px default) even
      // when outline-style is 'none' — the outline simply isn't drawn. The
      // "no indicator at rest" invariant is therefore style-based.
      expect(before.style, `${sel} shows an outline while unfocused`).toBe('none');

      await tabTo(page, sel);
      await expect
        .poll(async () => {
          const o = await outlineOf(sel);
          return o.focused && o.style === 'solid' && o.width >= 1;
        }, { timeout: 3_000 })
        .toBe(true);
    }
  });
});

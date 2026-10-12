const { test, expect } = require('@playwright/test');
const { selectPack } = require('./helpers');

async function answerAll(page) {
  const fields = page.locator('fieldset[data-qid]');
  for (let i = 0; i < await fields.count(); i++) {
    await fields.nth(i).locator('input[type=radio]').first().check();
  }
}

for (const failure of ['server', 'network']) {
  test(`quiz recovers from ${failure} failure without losing answers`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await selectPack(page, 'tidewatch', '#/quiz');
    await answerAll(page);
    const selected = await page.locator('input:checked').count();
    await page.route('**/api/v1/quiz/submit', async route => {
      if (failure === 'server') await route.fulfill({ status: 500, json: { detail: 'synthetic failure' } });
      else await route.abort('failed');
    }, { times: 1 });
    await page.locator('#quiz-submit').click();
    await expect(page.locator('#quiz-hint')).toContainText('may have processed');
    await expect(page.locator('#quiz-submit')).toBeEnabled();
    await expect(page.locator('input:checked')).toHaveCount(selected);
    await expect(page.locator('#quiz-score')).toBeEmpty();
    await expect(page.getByRole('button', { name: /download report/i })).toHaveCount(0);
    await page.locator('#quiz-submit').click();
    await expect(page.locator('#quiz-score')).toContainText('Score:');
    expect(errors).toEqual([]);
  });
}

test('pending old-view response cannot overwrite a newer quiz attempt', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await selectPack(page, 'tidewatch', '#/quiz');
  await answerAll(page);
  let release, started;
  const held = new Promise(resolve => release = resolve);
  const entered = new Promise(resolve => started = resolve);
  let requests = 0;
  await page.route('**/api/v1/quiz/submit', async route => {
    requests++;
    if (requests === 1) {
      started();
      await held;
      await route.fulfill({ json: { score: 999, total: 999, results: [] } });
    } else await route.continue();
  });
  await page.locator('#quiz-submit').click();
  await entered;
  await expect(page.locator('#quiz-submit')).toBeDisabled();
  await page.evaluate(() => submitQuiz());
  expect(requests).toBe(1);
  await page.locator('[data-nav="home"]').click();
  await expect(page.locator('#quiz-form')).toHaveCount(0);
  await page.getByRole('link', { name: 'Quiz', exact: true }).click();
  await expect(page.locator('#quiz-form')).toBeVisible();
  await answerAll(page);
  await page.locator('#quiz-submit').click();
  await expect(page.locator('#quiz-score')).toContainText('Score:');
  const score = await page.locator('#quiz-score').textContent();
  const finished = page.waitForResponse('**/api/v1/quiz/submit');
  release();
  await finished;
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect(page.locator('#quiz-score')).toHaveText(score);
  expect(score).not.toContain('999');
  expect(errors).toEqual([]);
});

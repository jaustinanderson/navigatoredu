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
      if (failure === 'server') await route.fulfill({ status: 500, json: { score: 999, total: 999, results: [] } });
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
  await page.evaluate(() => { window.__heldQuizAttempt = submitQuiz(); });
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
  await page.evaluate(() => window.__heldQuizAttempt);
  await expect(page.locator('#quiz-score')).toHaveText(score);
  expect(score).not.toContain('999');
  expect(errors).toEqual([]);
});

test('failed recheck clears previous grading borders and results', async ({ page }) => {
  await selectPack(page, 'tidewatch', '#/quiz');
  await answerAll(page);
  await page.locator('#quiz-submit').click();
  await expect(page.locator('#quiz-score')).toContainText('Score:');
  await page.route('**/api/v1/quiz/submit', route => route.fulfill({ status: 500, json: {} }));
  await page.locator('#quiz-submit').click();
  await expect(page.locator('#quiz-hint')).toContainText('may have processed');
  const fields = page.locator('fieldset[data-qid]');
  for (let i = 0; i < await fields.count(); i++) {
    await expect(fields.nth(i)).toHaveClass(/border-slate-200/);
    await expect(fields.nth(i)).not.toHaveClass(/border-green-600|border-red-400/);
    await expect(fields.nth(i).locator('.result')).toBeEmpty();
  }
  await expect(page.locator('#quiz-score')).toBeEmpty();
});

test('stalled submission times out and permits retry with answers retained', async ({ page }) => {
  await page.clock.install();
  await selectPack(page, 'tidewatch', '#/quiz');
  await answerAll(page);
  const count = await page.locator('input:checked').count();
  let entered;
  const started = new Promise(resolve => entered = resolve);
  await page.route('**/api/v1/quiz/submit', () => { entered(); }, { times: 1 });
  await page.locator('#quiz-submit').click();
  await started;
  await expect(page.locator('#quiz-submit')).toBeDisabled();
  await page.clock.runFor(15001);
  await expect(page.locator('#quiz-hint')).toContainText('may have processed');
  await expect(page.locator('#quiz-submit')).toBeEnabled();
  await expect(page.locator('input:checked')).toHaveCount(count);
  await page.locator('#quiz-submit').click();
  await expect(page.locator('#quiz-score')).toContainText('Score:');
});

for (const status of [400, 422]) {
  test(`quiz ${status} rejection asks learner to reopen questions`, async ({ page }) => {
    await selectPack(page, 'tidewatch', '#/quiz');
    await answerAll(page);
    await page.route('**/api/v1/quiz/submit', route => route.fulfill({ status, json: { detail: 'synthetic rejection' } }));
    await page.locator('#quiz-submit').click();
    await expect(page.locator('#quiz-hint')).toContainText('Reopen the Quiz');
    await expect(page.locator('#quiz-hint')).not.toContainText('may have processed');
    await expect(page.locator('#quiz-submit')).toBeEnabled();
    await expect(page.locator('#quiz-score')).toBeEmpty();
  });
}

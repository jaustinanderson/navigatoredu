// Quiz report download (spec 4) and the API-docs smoke (spec 5).
const fs = require('fs');
const { test, expect } = require('@playwright/test');
const { selectPack } = require('./helpers');

test('quiz: check answers, download report, verify the file', async ({ page }) => {
  await selectPack(page, 'tidewatch', '#/quiz');

  // Answer every question (first option) so submission is complete.
  const fieldsets = page.locator('fieldset[data-qid]');
  const n = await fieldsets.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    await fieldsets.nth(i).locator('input[type=radio]').first().check();
  }

  await page.locator('#quiz-submit').click();
  await expect(page.locator('#quiz-score')).toContainText(/Score: \d+ \/ \d+/);

  // Download-report button appears only after grading.
  const dlBtn = page.getByRole('button', { name: /download report/i });
  await expect(dlBtn).toBeVisible();

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    dlBtn.click(),
  ]);
  expect(download.suggestedFilename()).toBe('navigatoredu-quiz-report.html');
  const path = await download.path();
  expect(path).toBeTruthy();

  const html = fs.readFileSync(path, 'utf-8');
  expect(html.length).toBeGreaterThan(500);
  expect(html).toContain('NavigatorEdu');
  expect(html).toContain('Quiz Learning Report');
  expect(html).toMatch(/\d+ \/ \d+ \(\d+%\)/);           // score summary
  expect(html).toContain('Generated locally from submitted answers; not stored.');
  expect(html).not.toContain('<script');                  // self-contained + safe
});

test('API docs load and the OpenAPI schema names the app', async ({ page }) => {
  const schema = await (await page.request.get('/openapi.json')).json();
  expect(schema.info.title).toBe('NavigatorEdu API');
  expect(Object.keys(schema.paths)).toContain('/api/v1/quiz/report');

  await page.goto('/docs');
  await expect(page.locator('#swagger-ui')).toBeVisible();
  await expect(page.locator('body')).toContainText('NavigatorEdu API');
});

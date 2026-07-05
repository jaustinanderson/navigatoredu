// Playwright configuration for NavigatorEdu's browser tests.
//
// Reproducibility choice: Playwright launches the app itself (webServer
// below), reseeding a fresh database first, so `npm run test:browser` is the
// whole story — no separate terminal, no assumed state. Note this resets the
// local demo database (data/navigatoredu.db); that file is a rebuildable
// artifact by design (clear-then-load seeding), so nothing of value is lost.
//
// Pack switching is real server state, so tests run serially (workers: 1)
// and each spec selects the pack it needs through the app's own endpoints.
//
// These tests are dev/test-only. The application has no runtime dependency
// on Node or Playwright.
const { defineConfig } = require('@playwright/test');

const PORT = 8322;

module.exports = defineConfig({
  testDir: 'tests/browser',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
  },
  webServer: {
    command:
      `rm -f data/navigatoredu.db && python -m backend.app.seed && ` +
      `uvicorn backend.app.main:app --host 127.0.0.1 --port ${PORT}`,
    url: `http://127.0.0.1:${PORT}/api/v1/categories`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});

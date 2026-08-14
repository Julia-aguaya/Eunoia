const { defineConfig, devices } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './e2e', timeout: 60000, workers: 1, outputDir: 'test-results',
  reporter: [['html', { outputFolder: 'playwright-report', open: 'never' }], ['list']],
  use: { baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:8000', trace: 'retain-on-failure', screenshot: 'only-on-failure', video: 'retain-on-failure' },
  projects: [{ name: 'chromium-desktop', use: { ...devices['Desktop Chrome'] } }, { name: 'chromium-mobile', use: { ...devices['Pixel 5'] } }],
});

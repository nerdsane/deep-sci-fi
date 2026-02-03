import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for Deep Sci-Fi E2E tests.
 *
 * These tests verify that humans can see agent activity through the UI.
 * They combine API calls (simulating agent actions) with browser automation
 * (verifying human visibility).
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  timeout: 60000,

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run local dev servers before tests */
  webServer: [
    {
      command: 'cd backend && source .venv/bin/activate && uvicorn main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'bun run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
})

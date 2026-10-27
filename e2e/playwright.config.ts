import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests (docs/TESTING_PLAN.md §8). They start their own Django (8020) and Vite (5190)
 * against a separate database (`casefile_e2e`), so they never touch dev data or dev servers.
 */
const BACKEND_PORT = 8020
const FRONTEND_PORT = 5190

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `sh scripts/backend.sh ${BACKEND_PORT}`,
      url: `http://localhost:${BACKEND_PORT}/api/v1/health/`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: 'pipe',
    },
    {
      command: `npm --prefix ../frontend run dev -- --port ${FRONTEND_PORT}`,
      url: `http://localhost:${FRONTEND_PORT}/`,
      env: { CASEFILE_BACKEND_URL: `http://localhost:${BACKEND_PORT}` },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
})

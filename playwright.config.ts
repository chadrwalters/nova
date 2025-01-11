/// <reference types="node" />
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60000,
  retries: 2,
  workers: 3,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'cd src/nova/frontend && npm start',
    url: 'http://localhost:3001',
    timeout: 120000,
    reuseExistingServer: true,
  },
  projects: [
    {
      name: 'chromium',
      testMatch: ['**/*.test.ts', '**/visual.spec.ts'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    {
      name: 'webkit',
      testMatch: ['**/*.test.ts', '**/visual.spec.ts'],
      use: {
        ...devices['Desktop Safari'],
      },
    },
  ],
});

import { defineConfig, devices } from '@playwright/test';

// Lightweight config dedicated to recording demo videos. Not the project's
// general E2E rig — just enough to drive a single chromium instance with
// video capture. Uses dev server already running on :3000.
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 5 * 60 * 1000,           // analyses can take 60-90s
  fullyParallel: false,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    video: { mode: 'on', size: { width: 1280, height: 800 } },
    viewport: { width: 1280, height: 800 },
    headless: true,                 // viewport-recorded direct to .webm, no window needed
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});

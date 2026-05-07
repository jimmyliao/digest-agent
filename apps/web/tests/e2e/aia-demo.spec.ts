import { test, expect } from '@playwright/test';

/**
 * AIA Showcase 90s demo video.
 *
 * Pacing: real ADK run finishes in ~6-10s on cached news, so the storyboard
 * front-loads slow page tours + post-analysis browsing to land near 90s.
 *
 * Output: test-results/.../video.webm (single chromium video file).
 * Convert + (optionally) speed-balance with ffmpeg afterwards.
 */

const PAGES_TO_TOUR = [
  { url: '/', label: 'home' },
  { url: '/publish', label: 'pipeline' },
  { url: '/articles', label: 'articles' },
  { url: '/tasks', label: 'tasks' },
];

const STOCK_QUERY = '近期台積電 vs 聯發科 vs 鴻海';

async function smoothScrollDown(page: import('@playwright/test').Page) {
  await page.evaluate(() => {
    return new Promise<void>((resolve) => {
      const totalH = document.body.scrollHeight - window.innerHeight;
      if (totalH <= 0) return resolve();
      const steps = 60;          // 60 × 100ms = 6s glide
      const dy = totalH / steps;
      let i = 0;
      const id = setInterval(() => {
        window.scrollBy({ top: dy, behavior: 'auto' });
        i++;
        if (i >= steps) {
          clearInterval(id);
          setTimeout(resolve, 600);
        }
      }, 100);
    });
  });
}

test('aia-90s-demo', async ({ page }) => {
  // ── 0-40s: tour the four main pages (~10s each) ─────────────────────────
  for (const { url, label } of PAGES_TO_TOUR) {
    await page.goto(url);
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
    await page.waitForTimeout(1500);          // settle / read header
    await smoothScrollDown(page);
    await page.waitForTimeout(1500);          // dwell at bottom
    console.log(`[demo] toured ${label}`);
  }

  // ── 40-50s: land on stock-analysis, show dropdown / state ───────────────
  await page.goto('/stock-analysis');
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {});
  await page.waitForTimeout(2000);            // viewer reads header
  await smoothScrollDown(page);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await page.waitForTimeout(1500);

  // ── 50-58s: type query (slowly so it reads on screen) ───────────────────
  const input = page.getByPlaceholder('例如：2330 台積電、鴻海、聯發科');
  await input.click();
  await input.fill('');
  await input.pressSequentially(STOCK_QUERY, { delay: 120 });   // ~2s for 17 chars
  await page.waitForTimeout(1500);

  // ── 58-70s: kick off analysis, watch streaming ──────────────────────────
  await page.getByRole('button', { name: /開始分析/ }).click();
  console.log('[demo] analysis started');

  // Wait for the run to finish — button reverts from "🤖 分析中..." to "🔍 開始分析".
  // 3 min cap is generous; recent runs finished in 6-10s.
  await expect(
    page.getByRole('button', { name: /開始分析/ })
  ).toBeEnabled({ timeout: 180_000 });
  console.log('[demo] analysis done');

  // Pad analysis section with a viewing pause so streaming output is on-screen.
  await page.waitForTimeout(2000);

  // ── 70-82s: scroll up to show final report from top ─────────────────────
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await page.waitForTimeout(2500);
  await smoothScrollDown(page);
  await page.waitForTimeout(1500);

  // ── 82-90s: history dropdown demo (server-side feature highlight) ───────
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
  await page.waitForTimeout(800);

  // Open dropdown to show history breadth
  const dropdown = page.getByRole('combobox');
  await dropdown.click();
  await page.waitForTimeout(1500);
  await dropdown.press('Escape');             // close without selecting
  await page.waitForTimeout(2000);            // final beat

  console.log('[demo] storyboard complete');
});

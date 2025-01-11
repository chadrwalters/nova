import { test } from '@playwright/test';
import { expectScreenshotMatch, setViewportSize, waitForDataLoad } from './helpers';

test.describe('Visual Regression Tests', () => {
  test('dashboard layout matches snapshot', async ({ page }) => {
    await page.goto('/');
    await waitForDataLoad(page);
    await expectScreenshotMatch(page, 'dashboard-layout.png');
  });

  test('responsive layouts match snapshots', async ({ page }) => {
    await page.goto('/');

    // Desktop
    await setViewportSize(page, 1920, 1080);
    await expectScreenshotMatch(page, 'dashboard-desktop.png');

    // Tablet
    await setViewportSize(page, 768, 1024);
    await expectScreenshotMatch(page, 'dashboard-tablet.png');

    // Mobile
    await setViewportSize(page, 375, 812);
    await expectScreenshotMatch(page, 'dashboard-mobile.png');
  });

  test('dark mode matches snapshot', async ({ page }) => {
    await page.goto('/');
    await waitForDataLoad(page);
    await page.emulateMedia({ colorScheme: 'dark' });
    await expectScreenshotMatch(page, 'dashboard-dark.png');
  });
});

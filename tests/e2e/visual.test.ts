import { expect, test, waitForComponent, waitForDataLoad } from './fixtures';

test.describe('Visual Regression Tests', () => {
  test.beforeEach(async ({ page, loginAsAdmin }) => {
    await loginAsAdmin;
    await page.waitForLoadState('domcontentloaded');
    await page.waitForLoadState('networkidle');
  });

  test('dashboard layout matches snapshot', async ({ page }) => {
    await waitForDataLoad(page);

    // Wait for key components to be visible
    await expect(page.getByText('Service Health Overview')).toBeVisible();
    await expect(page.locator('[data-testid="error-metrics"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-table"]')).toBeVisible();

    // Take screenshot
    await expect(page).toHaveScreenshot('dashboard.png');
  });

  test('service health component matches snapshot', async ({ page }) => {
    await waitForComponent(page, 'service-health');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="service-health"]')).toHaveScreenshot('service-health.png', {
      mask: [page.locator('[data-testid="uptime-value"]')],
      timeout: 30000,
    });
  });

  test('error metrics component matches snapshot', async ({ page }) => {
    await waitForComponent(page, 'error-metrics');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="error-metrics"]')).toHaveScreenshot('error-metrics.png', {
      mask: [page.locator('[data-testid="error-chart"]')],
      timeout: 30000,
    });
  });

  test('alert table matches snapshot', async ({ page }) => {
    await waitForComponent(page, 'alert-table');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="alert-table"]')).toHaveScreenshot('alert-table.png', {
      mask: [
        page.locator('[data-testid="alert-time"]'),
        page.locator('[data-testid="alert-message"]'),
      ],
      timeout: 30000,
    });
  });

  test('theme switching visual consistency', async ({ page }) => {
    await waitForDataLoad(page);

    // Test light theme
    await expect(page).toHaveScreenshot('dashboard-light.png', {
      fullPage: true,
      mask: [page.locator('[data-testid="dynamic-content"]')],
      timeout: 30000,
    });

    // Switch to dark theme
    await waitForComponent(page, 'theme-toggle');
    await page.click('[data-testid="theme-toggle"]');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('dashboard-dark.png', {
      fullPage: true,
      mask: [page.locator('[data-testid="dynamic-content"]')],
      timeout: 30000,
    });
  });

  test('responsive layouts match snapshots', async ({ page }) => {
    // Mobile layout
    await page.setViewportSize({ width: 375, height: 667 });
    await waitForDataLoad(page);
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('dashboard-mobile.png', {
      fullPage: true,
      mask: [page.locator('[data-testid="dynamic-content"]')],
      timeout: 30000,
    });

    // Tablet layout
    await page.setViewportSize({ width: 768, height: 1024 });
    await waitForDataLoad(page);
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('dashboard-tablet.png', {
      fullPage: true,
      mask: [page.locator('[data-testid="dynamic-content"]')],
      timeout: 30000,
    });

    // Desktop layout
    await page.setViewportSize({ width: 1440, height: 900 });
    await waitForDataLoad(page);
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('dashboard-desktop.png', {
      fullPage: true,
      mask: [page.locator('[data-testid="dynamic-content"]')],
      timeout: 30000,
    });
  });

  test('preferences dialog matches snapshot', async ({ page }) => {
    await page.click('[data-testid="preferences-button"]');
    await expect(page.locator('[data-testid="preferences-dialog"]')).toHaveScreenshot('preferences-dialog.png');
  });

  test('saved searches dialog matches snapshot', async ({ page }) => {
    await page.click('[data-testid="saved-searches"]');
    await expect(page.locator('[data-testid="saved-searches-dialog"]')).toHaveScreenshot('saved-searches-dialog.png');
  });
});

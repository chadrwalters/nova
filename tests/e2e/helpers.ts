import { Page, expect } from '@playwright/test';

export async function waitForDataLoad(page: Page) {
  // Wait for the DOM content to be loaded
  await page.waitForLoadState('domcontentloaded');

  // Wait for critical components to be visible
  await Promise.all([
    page.getByText('Service Health Status').waitFor({ state: 'visible', timeout: 30000 }),
    page.locator('[data-testid="error-metrics"]').waitFor({ state: 'visible', timeout: 30000 }),
    page.locator('[data-testid="alert-table"]').waitFor({ state: 'visible', timeout: 30000 }),
  ]);

  // Wait for network to be idle
  await page.waitForLoadState('networkidle');
}

export async function expectScreenshotMatch(page: Page, name: string) {
  await expect(page).toHaveScreenshot(name, {
    timeout: 30000,
    mask: [
      page.locator('text=Service Health Status'),
      page.locator('[data-testid="error-metrics"]'),
      page.locator('[data-testid="alert-table"]'),
    ],
  });
}

export async function setViewportSize(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await waitForDataLoad(page);
}

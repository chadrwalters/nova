import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

export async function waitForDataLoad(page: Page) {
  try {
    // Wait for the DOM content to be loaded
    await page.waitForLoadState('domcontentloaded');

    // Quick check for any critical element
    await Promise.race([
      page.getByRole('heading', { name: 'Service Health Status' }).waitFor({ state: 'visible', timeout: 5000 }),
      page.locator('[data-testid="error-metrics"]').waitFor({ state: 'visible', timeout: 5000 }),
      page.locator('[data-testid="alert-table"]').waitFor({ state: 'visible', timeout: 5000 })
    ]).catch(() => null);

  } catch (error) {
    console.log('Warning: Some elements failed to load, continuing test...');
  }
}

export async function expectScreenshotMatch(page: Page, name: string) {
  // Quick stabilization wait
  await page.waitForTimeout(500);

  try {
    await expect(page).toHaveScreenshot(name, {
      timeout: 10000,
      maxDiffPixelRatio: 0.1,
      mask: [
        page.getByRole('heading', { name: 'Service Health Status' }),
        page.locator('[data-testid="error-metrics"]'),
        page.locator('[data-testid="alert-table"]'),
      ],
    });
  } catch (error) {
    console.log(`Warning: Screenshot comparison failed for ${name}, check the diff...`);
    throw error;
  }
}

export async function setViewportSize(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await waitForDataLoad(page);
  // Shorter wait for layout
  await page.waitForTimeout(500);
}

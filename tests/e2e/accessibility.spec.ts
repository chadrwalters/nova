import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should not have any automatically detectable accessibility issues', async ({ page }) => {
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('main navigation is keyboard accessible', async ({ page }) => {
    // Test tab navigation
    await page.keyboard.press('Tab');
    const firstFocused = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));
    expect(firstFocused).toBeTruthy();

    // Navigate through all focusable elements
    const focusableElements = await page.$$('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    for (let i = 0; i < focusableElements.length; i++) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => document.activeElement?.tagName);
      expect(focused).toBeTruthy();
    }
  });

  test('all images have alt text', async ({ page }) => {
    const images = await page.$$('img');
    for (const image of images) {
      const altText = await image.getAttribute('alt');
      expect(altText).toBeTruthy();
    }
  });

  test('color contrast meets WCAG standards', async ({ page }) => {
    const results = await new AxeBuilder({ page })
      .withRules(['color-contrast'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('interactive elements have accessible names', async ({ page }) => {
    const results = await new AxeBuilder({ page })
      .withRules(['button-name', 'link-name', 'aria-input-field-name'])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});

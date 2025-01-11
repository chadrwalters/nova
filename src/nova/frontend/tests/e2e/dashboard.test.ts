import { expect, test } from '@playwright/test';
import { waitForDataLoad } from './helpers';

test.describe('Dashboard Hero Tests', () => {
  test('initial dashboard load shows all components', async ({ page }) => {
    await page.goto('/');
    await waitForDataLoad(page);

    // Check if all components are visible using more specific selectors
    await expect(page.getByRole('heading', { name: 'Service Health Status' })).toBeVisible();
    await expect(page.locator('[data-testid="error-metrics"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-table"]')).toBeVisible();
  });

  test('service health component shows status filter', async ({ page }) => {
    await page.goto('/');
    await waitForDataLoad(page);

    // Check if filter is present and interactive using aria-label
    const filterSelect = page.getByRole('combobox', { name: 'Filter by Status' });
    await expect(filterSelect).toBeVisible();
    await filterSelect.click();

    // Check filter options using listbox role
    const listbox = page.getByRole('listbox');
    await expect(listbox).toBeVisible();
    await expect(page.getByRole('option', { name: 'All Services' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Healthy' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Warning' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Error' })).toBeVisible();
  });

  test('error metrics component shows severity filter', async ({ page }) => {
    await page.goto('/');
    await waitForDataLoad(page);

    // Check if filter is present and interactive using aria-label
    const filterSelect = page.getByRole('combobox', { name: 'Filter by Severity' });
    await expect(filterSelect).toBeVisible();
    await filterSelect.click();

    // Check filter options using listbox role
    const listbox = page.getByRole('listbox');
    await expect(listbox).toBeVisible();
    await expect(page.getByRole('option', { name: 'All Severities' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Low' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Medium' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'High' })).toBeVisible();
    await expect(page.getByRole('option', { name: 'Critical' })).toBeVisible();
  });

  test('alert table shows headers and sample data', async ({ page }) => {
    await page.goto('/');
    await waitForDataLoad(page);

    // Check table headers
    await expect(page.getByRole('columnheader', { name: 'Time' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Severity' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Message' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();

    // Check sample data
    await expect(page.locator('[data-testid="alert-time"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-message"]')).toBeVisible();
  });
});

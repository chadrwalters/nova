import {
    acknowledgeAlert,
    createSavedSearch,
    customizeLayout,
    expect,
    exportMetrics,
    filterErrorsByCategory,
    filterErrorsBySeverity,
    loadSavedSearch,
    resolveAlert,
    setTimeRange,
    test,
    toggleTheme,
    waitForDataLoad
} from './fixtures';

test.describe('Dashboard Hero Tests', () => {
  test.beforeEach(async ({ page, loginAsAdmin }) => {
    await loginAsAdmin;
    await waitForDataLoad(page);
  });

  test('initial dashboard load shows all components', async ({ page }) => {
    await page.goto('/');
    await waitForDataLoad(page);

    // Check if all components are visible
    await expect(page.getByText('Service Health Status')).toBeVisible();
    await expect(page.locator('[data-testid="error-metrics"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-table"]')).toBeVisible();
  });

  test('service health monitoring workflow', async ({ page }) => {
    // Wait for service health overview to be visible
    await expect(page.getByText('Service Health Status')).toBeVisible();

    // Test status filtering
    const filterSelect = page.locator('text=Filter by Status');
    await expect(filterSelect).toBeVisible();
    await filterSelect.click();

    // Check filter options
    await expect(page.getByText('All Services')).toBeVisible();
    await expect(page.getByText('Healthy')).toBeVisible();
    await expect(page.getByText('Warning')).toBeVisible();
    await expect(page.getByText('Error')).toBeVisible();
  });

  test('error metrics filtering and search', async ({ page }) => {
    // Test category filtering
    await filterErrorsByCategory(page, 'API');
    await expect(page.locator('[data-testid="error-chart"]')).toBeVisible();

    // Test severity filtering
    await filterErrorsBySeverity(page, 'CRITICAL');
    await expect(page.locator('[data-testid="error-chart"]')).toBeVisible();
  });

  test('alert management lifecycle', async ({ page }) => {
    const alertId = 'test-alert-1';

    // Test alert acknowledgment
    await acknowledgeAlert(page, alertId);
    await expect(page.locator(`[data-testid="alert-status-${alertId}"]`)).toHaveText('ACKNOWLEDGED');

    // Test alert resolution
    await resolveAlert(page, alertId);
    await expect(page.locator(`[data-testid="alert-status-${alertId}"]`)).toHaveText('RESOLVED');
  });

  test('user preferences persistence', async ({ page }) => {
    // Test theme switching
    await toggleTheme(page);
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.reload();
    await waitForDataLoad(page);
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    // Test layout customization
    await customizeLayout(page, 'service-health', 'layout-target');
    await page.reload();
    await waitForDataLoad(page);
    await expect(page.locator('[data-testid="service-health"]')).toHaveAttribute('data-grid-area', 'area-1');
  });

  test('saved searches functionality', async ({ page }) => {
    // Create and verify saved search
    await createSavedSearch(page, 'api', 'API Components');
    await page.reload();
    await waitForDataLoad(page);

    // Load and verify saved search
    await loadSavedSearch(page, 'API Components');
    await expect(page.locator('[data-testid="component-search"]')).toHaveValue('api');
  });

  test('responsive design validation', async ({ page }) => {
    // Test mobile layout
    await page.setViewportSize({ width: 375, height: 667 });
    await waitForDataLoad(page);
    await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible();

    // Test tablet layout
    await page.setViewportSize({ width: 768, height: 1024 });
    await waitForDataLoad(page);
    await expect(page.locator('[data-testid="tablet-layout"]')).toBeVisible();

    // Test desktop layout
    await page.setViewportSize({ width: 1440, height: 900 });
    await waitForDataLoad(page);
    await expect(page.locator('[data-testid="desktop-layout"]')).toBeVisible();
  });

  test('data export functionality', async ({ page }) => {
    const download = await exportMetrics(page);
    expect(download.suggestedFilename()).toContain('.csv');
  });

  test('performance benchmarks', async ({ page }) => {
    // Test initial load time
    const startTime = Date.now();
    await page.reload();
    await waitForDataLoad(page);
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000); // 3s threshold

    // Test chart render time
    const chartStartTime = Date.now();
    await setTimeRange(page, '1d');
    await page.waitForSelector('[data-testid="chart-rendered"]');
    const chartRenderTime = Date.now() - chartStartTime;
    expect(chartRenderTime).toBeLessThan(1000); // 1s threshold
  });
});

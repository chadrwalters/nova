import type { Page } from '@playwright/test';
import { test as base } from '@playwright/test';

// Mock API responses
const mockServiceHealth = {
  health_score: 95.5,
  uptime_history: {
    timestamps: ['2024-01-20T10:00:00Z', '2024-01-20T10:15:00Z', '2024-01-20T10:30:00Z'],
    values: [99.9, 99.8, 99.9]
  },
  component_status: {
    'API Gateway': { status: 'healthy', uptime_percentage: 99.9 },
    'Database': { status: 'degraded', uptime_percentage: 95.5, last_error: 'High latency' },
    'Cache': { status: 'healthy', uptime_percentage: 99.8 }
  }
};

const mockServiceErrors = {
  api_errors: 5,
  rate_limits_remaining: 95,
  error_count_history: [10, 8, 5],
  error_rate_history: [2.5, 2.0, 1.5],
  timestamps: ['2024-01-20T10:00:00Z', '2024-01-20T10:15:00Z', '2024-01-20T10:30:00Z']
};

// Extend basic test fixture with custom utilities
export const test = base.extend<{
  loginAsAdmin: void;
}>({
  // Auto-login before each test
  loginAsAdmin: async ({ page }, use) => {
    await page.goto('/');

    // Mock API responses
    await page.route('/api/services/health', async (route) => {
      await route.fulfill({ json: mockServiceHealth });
    });

    await page.route('/api/services/errors', async (route) => {
      await route.fulfill({ json: mockServiceErrors });
    });

    await use();
  },
});

export { expect } from '@playwright/test';

// Helper functions
export async function waitForDataLoad(page: Page, timeout = 30000) {
  // Wait for loading skeleton to disappear
  try {
    await page.waitForSelector('[data-testid="loading-skeleton"]', {
      state: 'hidden',
      timeout
    });
  } catch (e) {
    console.log('Loading skeleton not found, proceeding with component checks');
  }

  // Wait for critical components
  const components = ['error-metrics', 'alert-table'];
  for (const component of components) {
    try {
      await page.waitForSelector(`[data-testid="${component}"]`, {
        state: 'visible',
        timeout
      });
    } catch (e) {
      console.log(`Component ${component} not found within ${timeout}ms`);
    }
  }

  // Wait for Service Health Overview text
  try {
    await page.getByText('Service Health Overview').waitFor({ state: 'visible', timeout });
  } catch (e) {
    console.log('Service Health Overview text not found within ${timeout}ms');
  }

  // Wait for network to be idle
  await page.waitForLoadState('networkidle', { timeout });
}

export async function waitForComponent(page: Page, testId: string) {
  const timeout = 30000;
  try {
    await page.waitForSelector(`[data-testid="${testId}"]`, {
      state: 'visible',
      timeout
    });
    console.log(`Component ${testId} is visible`);
  } catch (e) {
    console.log(`Timeout waiting for ${testId}`);
    throw e;
  }
}

export async function setTimeRange(page: Page, range: string) {
  await waitForComponent(page, 'time-range-selector');
  await page.click('[data-testid="time-range-selector"]');
  await page.click(`[data-testid="time-range-${range}"]`);
  await waitForDataLoad(page);
}

export async function filterByStatus(page: Page, status: string) {
  await waitForComponent(page, 'status-filter');
  await page.selectOption('[data-testid="status-filter"]', status);
  await waitForDataLoad(page);
}

export async function searchComponents(page: Page, query: string) {
  await waitForComponent(page, 'component-search');
  await page.fill('[data-testid="component-search"]', query);
  await waitForDataLoad(page);
}

export async function filterErrorsByCategory(page: Page, category: string) {
  await waitForComponent(page, 'error-category-filter');
  await page.click('[data-testid="error-category-filter"]');
  await page.click(`[data-testid="category-${category}"]`);
  await waitForDataLoad(page);
}

export async function filterErrorsBySeverity(page: Page, severity: string) {
  await waitForComponent(page, 'error-severity-filter');
  await page.click('[data-testid="error-severity-filter"]');
  await page.click(`[data-testid="severity-${severity}"]`);
  await waitForDataLoad(page);
}

export async function createSavedSearch(page: Page, query: string, name: string) {
  await searchComponents(page, query);
  await waitForComponent(page, 'save-search');
  await page.click('[data-testid="save-search"]');
  await page.fill('[data-testid="search-name"]', name);
  await page.click('[data-testid="confirm-save"]');
}

export async function loadSavedSearch(page: Page, name: string) {
  await waitForComponent(page, 'saved-searches');
  await page.click('[data-testid="saved-searches"]');
  await page.click(`[data-testid="load-search-${name}"]`);
  await waitForDataLoad(page);
}

export async function toggleTheme(page: Page) {
  await waitForComponent(page, 'theme-toggle');
  await page.click('[data-testid="theme-toggle"]');
}

export async function customizeLayout(page: Page, componentId: string, targetArea: string) {
  await waitForComponent(page, 'customize-layout');
  await page.click('[data-testid="customize-layout"]');
  await page.dragAndDrop(`[data-testid="${componentId}"]`, `[data-testid="${targetArea}"]`);
  await page.click('[data-testid="save-layout"]');
}

export async function exportMetrics(page: Page) {
  await waitForComponent(page, 'export-metrics');
  await page.click('[data-testid="export-metrics"]');
  return await page.waitForEvent('download');
}

export async function acknowledgeAlert(page: Page, alertId: string) {
  await waitForComponent(page, `acknowledge-alert-${alertId}`);
  await page.click(`[data-testid="acknowledge-alert-${alertId}"]`);
  await waitForDataLoad(page);
}

export async function resolveAlert(page: Page, alertId: string) {
  await waitForComponent(page, `resolve-alert-${alertId}`);
  await page.click(`[data-testid="resolve-alert-${alertId}"]`);
  await waitForDataLoad(page);
}

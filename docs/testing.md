# Testing Guide

## Getting Started

1. **Start Development Server**
   ```bash
   # Start the development server
   npm run start

   # Verify it's running by checking:
   # ➜  Local:   http://localhost:3000/
   ```

2. **Install Test Dependencies**
   ```bash
   # Install Playwright browsers
   npx playwright install webkit chrome
   ```

3. **Run Tests**
   ```bash
   # Run tests in Safari (default)
   npm run test:e2e

   # Or with snapshot updates
   npm run test:e2e:update
   ```

4. **View Results**
   ```bash
   # After tests complete, view the HTML report
   npx playwright show-report
   ```

## Browser Support

Nova's testing infrastructure is configured to run primarily on Safari (WebKit) by default, with optional Chrome (Chromium) testing support. This configuration aligns with our development environment and ensures consistent testing across environments.

### Default Browser (Safari)
- All tests run on Safari by default
- Uses WebKit engine
- Matches the primary development environment

### Optional Chrome Testing
- Chrome testing can be enabled via environment variable
- Useful for cross-browser verification
- Particularly helpful for CI/CD pipelines

## Test Commands

```bash
# Run tests in Safari (default)
npm run test:e2e

# Run tests in Safari and update snapshots
npm run test:e2e:update

# Run tests in Chrome
npm run test:e2e:chrome

# Run tests in Chrome and update snapshots
npm run test:e2e:chrome:update
```

## Test Configuration

The test configuration is managed through `playwright.config.ts` with the following key settings:

```typescript
{
  timeout: 60000,        // 60 second timeout
  retries: 2,           // Retry failed tests twice
  workers: 4,           // Run 4 parallel test workers
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    timeout: 120000,
    reuseExistingServer: true  // In non-CI environments
  }
}
```

### Visual Regression Tests
- Snapshots are browser-specific
- Use `UPDATE_SNAPSHOTS=1` to update baseline images
- Stored in `test-results` directory

### Test Files
- `*.test.ts`: Standard test files
- `visual.spec.ts`: Visual regression tests
- `accessibility.spec.ts`: Accessibility tests

## Best Practices

1. **Browser Testing**
   - Always test in Safari first (default environment)
   - Use Chrome testing for cross-browser verification
   - Update snapshots for each browser separately

2. **Visual Testing**
   - Keep baseline images up to date
   - Review visual changes carefully
   - Consider viewport sizes in visual tests

3. **Test Organization**
   - Group related tests in describe blocks
   - Use clear, descriptive test names
   - Follow the Arrange-Act-Assert pattern

4. **Performance**
   - Tests run in parallel (4 workers)
   - Reuse server when possible
   - Retry failed tests automatically

## Continuous Integration

- Tests run on Safari by default
- Chrome tests can be enabled with `RUN_CHROME=1`
- Both browsers can be tested in CI pipeline
- Snapshots should be updated deliberately

## Troubleshooting

1. **Snapshot Mismatches**
   - Run update command for specific browser
   - Review changes in test-results directory
   - Commit updated snapshots if changes are expected

2. **Timeouts**
   - Check server status
   - Verify component loading states
   - Adjust timeouts in config if needed

3. **Cross-browser Issues**
   - Test specifically in problematic browser
   - Check for browser-specific CSS
   - Verify component compatibility

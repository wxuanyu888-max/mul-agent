# E2E Testing with Playwright

This project uses Playwright for end-to-end testing of the frontend application.

## Running Tests

### Prerequisites

Make sure the backend server is running on port 8000:
```bash
python -m uvicorn mul_agent.api.server:app --host 0.0.0.0 --port 8000
```

And the frontend dev server is running on port 5182:
```bash
cd frontend && npm run dev
```

### Run All Tests

```bash
cd frontend
npm run test:e2e
```

### Run Tests with UI Mode

```bash
npm run test:e2e:ui
```

### Run Tests in Debug Mode

```bash
npm run test:e2e:debug
```

### Run Specific Test File

```bash
npx playwright test e2e/chat.spec.ts
```

### Run Specific Test

```bash
npx playwright test -g "should send a message"
```

### Run Tests for Specific Browser

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## Test Structure

Tests are located in `frontend/e2e/`:

- `app.spec.ts` - Application navigation and layout tests (8 tests)
- `chat.spec.ts` - Chat functionality and API integration tests (11 tests)
- `logs.spec.ts` - Logs viewer tests (2 tests)
- `memory.spec.ts` - Memory panel tests (2 tests)
- `token.spec.ts` - Token usage panel tests (10 tests)

**Total: 33 tests**

## Configuration

Playwright is configured in `playwright.config.ts`:

- Base URL: `http://localhost:5182` (or `FRONTEND_URL` env variable)
- Default browsers: Chromium, Firefox, WebKit
- Screenshots: Taken on failure only
- Video: Recorded on failure only
- Trace: Collected on first retry
- Test timeout: 30 seconds per test

## Viewing Test Results

After running tests, view the HTML report:

```bash
npx playwright show-report
```

## Test Artifacts

Failed tests generate artifacts in the `test-results/` directory:
- Screenshots
- Videos
- Trace files (for debugging)

## CI/CD Integration

The tests are configured to:
- Run in parallel locally
- Run sequentially on CI (`CI=true`)
- Retry failed tests twice on CI
- Forbid `test.only` in CI

## Test Coverage Summary

| Category | Tests | Status |
|----------|-------|--------|
| App Navigation | 8 | Stable |
| Chat | 11 | Stable |
| Logs | 2 | Stable |
| Memory | 2 | Stable |
| Token Usage | 10 | Stable |

## Known Issues

1. Tests may fail if the frontend dev server stops during test execution. Ensure `npm run dev` is running continuously.
2. The frontend dev server may stop due to inactivity. Keep the terminal active.

## Troubleshooting

### Tests fail with "ERR_CONNECTION_REFUSED"
- Restart the frontend dev server: `npm run dev`
- Ensure the backend is running on port 8000

### Tests timeout waiting for elements
- Increase timeout in `playwright.config.ts`
- Check if the frontend is properly loaded
- Verify the backend API is responding

#!/usr/bin/env bash
# Run Playwright E2E tests using system-installed browsers.
# Use this when "Executable doesn't exist" in Cursor sandbox.
# See docs/playwright-e2e.md for details.

export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}"
exec npx playwright test "$@"

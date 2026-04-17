# Plan: Opening Balance Setup Wizard

## Summary
Add a guided Opening Balances workflow that depends on a ready chart of accounts, supports manual balancing or optional auto-balance to equity, and posts the final result as a standard journal entry.

## Key Changes
- Add chart readiness settings metadata and helper logic with legacy fallback detection.
- Mark the chart as ready after template loads and successful Xero imports.
- Add opening-balance status/create API endpoints protected by `accounts.manage`.
- Add a new SPA page and Accounting nav entry for Opening Balances.
- Keep posting behavior on the existing journal engine so balances and reports stay consistent.

## Test Plan
- Backend tests for readiness markers, legacy fallback, rejection when not ready, and journal posting behavior.
- Frontend tests for the blocked state, ready state, auto-balance option, and route rendering.
- Run targeted Python/JS suites plus `git diff --check`.

## Assumptions
- Successful Xero import counts as chart-ready because it imports accounts before ledger history.
- Legacy databases with active asset/liability/equity accounts should remain eligible even without the new settings markers.
- v1 only supports balance-sheet opening balances.

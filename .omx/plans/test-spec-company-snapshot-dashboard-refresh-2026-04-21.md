# Test Spec — Company Snapshot dashboard refresh (Xero-inspired)

## Date
2026-04-21

## Red/Green plan
- Add/expand frontend dashboard tests first so the new widget layout and RBAC behavior are locked before implementation.
- Add backend route tests for the richer `/api/dashboard` and `/api/dashboard/charts` payload contract.
- Confirm targeted tests fail against the current dashboard.
- Implement the smallest backend aggregation + frontend rendering changes needed to satisfy the new contract.
- Re-run targeted dashboard tests and repo safety checks before concluding.

## Frontend verification targets
- `tests/js_dashboard_rbac_visibility.test.js`
  - financial users see the new Xero-style widget set
  - non-financial users still hide financial widgets and do not call `/dashboard/charts`
  - empty-state payloads render safe placeholders instead of broken tables/charts
- Add a focused dashboard layout/render test if the current file becomes too broad.

## Backend verification targets
- Extend or add backend tests for:
  - enriched `/api/dashboard` payload shape
  - enriched `/api/dashboard/charts` payload shape
  - financial permission gating
  - zero-data/new-company behavior
  - account watchlist and bank-summary aggregation correctness

## Safety checks
- `npm test -- tests/js_dashboard_rbac_visibility.test.js`
- targeted Python dashboard/report aggregation tests
- `git diff --check`

## Manual/visual checks
- Compare the refreshed dashboard against the Xero reference for layout hierarchy:
  - rounded widget cards
  - scannable top-row priorities
  - actionable buttons/links
  - readable mini charts in both light and dark mode

## Non-goals for this slice
- Replacing the full QuickBooks-inspired shell with a Xero clone
- Adding payroll/employee-sensitive widgets
- Reworking unrelated report screens beyond shared helper extraction

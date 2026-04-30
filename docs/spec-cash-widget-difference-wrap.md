# Cash Widget Difference Wrap Bugfix Specification

## Goal
The Company Snapshot cash in/out widget should remain readable when currency amounts are large by placing Difference on its own second row.

## Required Behavior
- Cash in and Cash out remain adjacent on the first row.
- Difference renders below them and spans the full widget width.
- Existing labels, values, currency formatting, chart bars, API calls, and permissions are unchanged.
- The layout continues to collapse cleanly on narrow screens.

## Constraints
- Presentation-only change; no dashboard API or permission changes.
- No new packages or charting libraries.
- Preserve dark-theme readability.

## Verification
- `node tests/js_dashboard_rbac_visibility.test.js`
- `node --check app/static/js/app.js`
- `git diff --check`
- Focused self-review of CSS layout, responsive behavior, and security impact.

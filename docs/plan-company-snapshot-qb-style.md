# Company Snapshot QB Style Cleanup Plan

## Objective
Make the Company Snapshot dashboard read more like the original QuickBooks-style dashboard chrome without changing the existing widget content or data flow.

## Constraints
- Keep the current widget set, copy, and dashboard data contracts intact.
- Limit the slice to presentation changes for box shapes, chart bars, and table borders.
- No new dependencies or dashboard route changes.

## Implementation Sketch
- Replace the rounded snapshot shell/card treatment with flatter QB-style panels, headers, and separators.
- Restyle comparison bars and cash-flow bars to use sharper rectangular geometry and more classic QB gradients/borders.
- Tighten the watchlist table frame/header/cell borders so it matches the older report-grid treatment.
- Keep dark-theme equivalents aligned with the light-theme changes.

## Impacted Files
- `app/static/js/app.js`
- `app/static/css/style.css`
- `app/static/css/dark.css`
- `tests/js_dashboard_rbac_visibility.test.js`

## Test Plan
- Add/update JS coverage for the dashboard markup classes that drive the refreshed QB-style chrome.
- Run the targeted dashboard JS test first.
- Run syntax/verification checks plus `git diff --check`.

## Risk Notes
- Pure CSS changes can unintentionally regress dark theme contrast or collapse widget spacing at smaller breakpoints.
- Dashboard markup changes must stay compatible with the current RBAC visibility behavior.

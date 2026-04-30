# Company Snapshot Profit Trend Alignment Fix Plan

## Objective
Fix the left-margin alignment of the net profit/loss helper text so it lines up with the widget's main numeric content.

## Constraints
- Keep the existing widget set, copy, and dashboard data flow unchanged.
- Limit the slice to the specific Company Snapshot profit widget alignment bug.
- No new dependencies or dashboard route changes.

## Implementation Sketch
- Add a dedicated markup hook for the profit trend/helper line.
- Apply widget-content padding through a scoped CSS rule so the helper text aligns with the big number without affecting other uses of `snapshot-trend`.
- Extend the dashboard render regression test with the new markup hook.

## Impacted Files
- `app/static/js/app.js`
- `app/static/css/style.css`
- `tests/js_dashboard_rbac_visibility.test.js`

## Test Plan
- Update the targeted dashboard JS render test for the new trend hook.
- Run the targeted dashboard JS test, JS syntax check, and `git diff --check`.

## Risk Notes
- Reusing the global `snapshot-trend` class for spacing would affect bank mini-card difference badges, so the fix must stay scoped to the profit widget.

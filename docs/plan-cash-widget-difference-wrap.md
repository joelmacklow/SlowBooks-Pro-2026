# Cash Widget Difference Wrap Bugfix Plan

## Objective
Prevent the Company Snapshot cash in/out widget from crowding or overflowing when cash amounts get large by moving the Difference metric onto a second row.

## Constraints
- Preserve the existing dashboard data contract, report link, labels, and currency formatting.
- Keep Cash in and Cash out side by side.
- Keep the change presentation-only; no API, permission, or chart logic changes.
- No new dependencies.

## Implementation Sketch
- Add a scoped presentation hook to the Difference metric in `renderDashboardCashFlowWidget`.
- Change the split metric grid to two columns so Cash in and Cash out remain on the first row.
- Make the Difference metric span the full grid width on the second row, with amount text allowed to wrap safely.
- Add a dark-theme border color for the new second-row separator.

## Impacted Files
- `app/static/js/app.js`
- `app/static/css/style.css`
- `app/static/css/dark.css`
- `tests/js_dashboard_rbac_visibility.test.js`

## Test Plan
- Update the dashboard JS regression test to render larger cash values and assert the Difference metric receives the scoped wrap hook.
- Run `node tests/js_dashboard_rbac_visibility.test.js`.
- Run `node --check app/static/js/app.js`.
- Run `git diff --check`.

## Risk Notes
- This is a low-risk dashboard presentation change.
- Main regression risk is unintentionally altering the existing RBAC-controlled dashboard rendering or mobile stacking behavior.

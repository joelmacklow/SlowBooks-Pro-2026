# Plan — Payroll timesheets admin UI surfacing

## Objective
Expose the new payroll timesheets admin review endpoints in the existing payroll UI so payroll staff can discover and use period/pay-run readiness, detail, correction, approval, rejection, bulk approval, audit, and export actions without leaving the payroll screen.

## Constraints
- Keep the change in the current web UI only; no backend slice work.
- Reuse the already-implemented `/api/timesheets/*` admin endpoints.
- Keep the payroll page readable; add a compact admin review panel rather than a separate app-wide navigation overhaul.
- Preserve existing payroll actions and tests.

## Implementation sketch
1. Add a timesheet review panel to `app/static/js/payroll.js` that only appears when the user has one of the new timesheet admin permissions.
2. Let payroll staff:
   - fetch period readiness,
   - open a pay-run readiness view,
   - view submitted timesheet details and audit history,
   - trigger approve/reject/correct/bulk-approve actions,
   - download a scoped CSV export.
3. Keep the panel compact and modal-driven so it does not crowd the existing pay-run table.
4. Add JS regression tests for the payroll page rendering and the new timesheet review actions.

## Impacted files
- `app/static/js/payroll.js`
- `tests/js_nz_payroll_ui.test.js`
- `tests/js_payroll_filing_audit_ui.test.js` if shared payroll rendering expectations need updates

## Test plan
- Add targeted JS tests first for rendering and action wiring.
- Run the affected JS tests plus `node --check` or the repository’s JS test command if available.
- Run `git diff --check`.

## Risk notes
- The payroll page already mixes several action groups; the new review panel should stay narrowly permission-gated so it does not expose timesheet admin controls to payroll viewers.
- UI wiring must not accidentally call the admin endpoints for users without the proper permissions.

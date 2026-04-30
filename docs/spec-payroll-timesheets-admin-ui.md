# Test Spec — Payroll timesheets admin UI surfacing

## Slice goal
Prove the payroll page surfaces the timesheet review endpoints in a discoverable, permission-gated way.

## Required behavior
- Payroll admins with timesheet permissions see a timesheet review panel on the payroll page.
- Payroll viewers without those permissions do not see the panel or its action buttons.
- The panel can load period readiness and a pay-run readiness view.
- The panel can open a timesheet detail/audit view and trigger approve, reject, correct, bulk approve, and export actions.
- Existing payroll render behavior remains intact.

## Tests to add
1. `test_payroll_page_includes_timesheet_review_panel_for_admins`
2. `test_payroll_page_hides_timesheet_review_panel_from_viewers`
3. `test_timesheet_review_panel_calls_period_readiness_and_export_endpoints`
4. `test_timesheet_review_panel_surfaces_pay_run_readiness_and_actions`

## Verification
- Run the targeted JS test file(s).
- Run `git diff --check`.

## Non-goals
- No backend changes.
- No new routes or navigation structure outside the payroll page.
- No employee self-service UI changes.

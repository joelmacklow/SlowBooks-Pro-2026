# Test Spec — Payroll timesheets admin review API

## Slice goal
Prove the admin review API for payroll timesheets works safely for authorised users and remains blocked for roles without explicit timesheet admin permissions.

## Required behavior
- Payroll admins can list timesheets for a period or pay run, grouped by status.
- Payroll admins can open submitted timesheet detail, including audit history.
- Payroll admins can correct submitted timesheets with a reason and keep them in submitted state.
- Payroll admins can approve, reject, and bulk approve submitted timesheets.
- Payroll admins can export a scoped CSV with safe headers and filename.
- Non-admin payroll roles cannot approve or export unless explicitly permissioned.

## Tests to add
1. `test_admin_can_list_period_readiness_grouped_by_status`
2. `test_admin_can_list_pay_run_readiness_grouped_by_status`
3. `test_admin_can_view_timesheet_detail_and_audit`
4. `test_admin_can_correct_submitted_timesheet_with_reason`
5. `test_admin_can_approve_reject_and_bulk_approve`
6. `test_admin_cannot_approve_invalid_or_locked_timesheets`
7. `test_viewer_role_cannot_approve_or_export_without_permission`
8. `test_admin_csv_export_is_scoped_and_filename_safe`

## Verification
- Run the new targeted admin route test file.
- Run `git diff --check`.
- If auth permissions change, run the focused RBAC regression test that covers payroll/timesheet roles.

## Non-goals
- No employee self-service behavior changes.
- No payroll import/locking slice work.
- No frontend/admin dashboard rendering changes.

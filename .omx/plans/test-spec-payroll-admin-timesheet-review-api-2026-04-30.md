# Test Spec: Payroll timesheet admin review API slice

## Scope
Verify the backend-only admin review API for timesheets. This spec covers permission gates, period readiness, admin list/detail, correction, approval/rejection, bulk approval, audit visibility, CSV export safety, and regressions for employee self-service boundaries.

## Primary acceptance mapping
- PRD: `.omx/plans/prd-payroll-admin-timesheet-review-api-2026-04-30.md`
- Parent feature PRD: `.omx/plans/prd-payroll-timesheets-2026-04-30.md`
- Parent todo: `.omx/plans/todo-payroll-timesheets-2026-04-30.md`

## Test fixtures
Create `tests/test_timesheets_admin_routes.py` with the same direct-route test style used by `tests/test_timesheets_self_service_routes.py`.

Shared fixture helpers should create:
- in-memory master and company SQLite sessions;
- owner/admin auth via bootstrap;
- payroll admin user/auth;
- payroll viewer user/auth;
- employee self-service user/auth;
- active hourly employees;
- inactive employee;
- salary employee where readiness should not require an hourly timesheet;
- draft, submitted, approved, rejected, and locked timesheets for one period.

## Required tests

### Permissions and role coverage
1. `test_payroll_admin_role_receives_admin_timesheet_permissions`
   - Assert `payroll_admin` can satisfy `timesheets.manage`, `timesheets.approve`, and `timesheets.export`.
   - Assert `payroll_viewer` and `employee_self_service` cannot satisfy those permissions.
2. `test_admin_endpoints_reject_employee_self_service_user`
   - Exercise representative list/detail/approve/export calls and assert HTTP 403.
3. `test_admin_endpoints_reject_payroll_viewer_user`
   - Assert read-only payroll viewer does not gain timesheet review access in this slice.

### Period readiness
4. `test_admin_readiness_reports_status_per_active_hourly_employee`
   - For the requested period, include active hourly employees with `not_started`, `draft`, `submitted`, `approved`, `rejected`, and `locked` states.
   - Assert each existing row includes the matching timesheet id and total hours.
5. `test_admin_readiness_excludes_inactive_and_salary_employees`
   - Inactive employees and salary employees should not create missing hourly-timesheet blockers in this MVP readiness view.
6. `test_admin_readiness_requires_valid_period`
   - Reject period start after period end with HTTP 400.

### Admin list and detail
7. `test_admin_list_filters_by_period_status_and_employee`
   - Create multiple employees/periods/statuses.
   - Assert filters return only matching company-local timesheets.
8. `test_admin_detail_returns_safe_employee_summary`
   - Assert response includes employee id/display name and timesheet lines/audit.
   - Assert response excludes `ird_number`, `tax_code`, `pay_rate`, and full employee ORM data.
9. `test_admin_detail_missing_id_returns_404`
   - Missing id maps to HTTP 404.

### Correction
10. `test_admin_corrects_submitted_timesheet_with_reason_and_audit`
   - Correct lines on a submitted timesheet.
   - Assert total recalculates, actor id is recorded, and latest audit event action/reason reflect correction.
11. `test_admin_correction_requires_reason`
   - Empty or whitespace reason returns HTTP 400 and leaves existing lines unchanged.
12. `test_admin_correction_blocks_approved_and_locked_timesheets`
   - Approved and locked records cannot be silently edited.
13. `test_admin_correction_validates_lines_with_existing_rules`
   - Out-of-period work date, invalid duration, and invalid start/end/break inputs return HTTP 400.

### Approval and rejection
14. `test_admin_approves_submitted_timesheet_and_records_actor`
   - Submitted → approved.
   - Assert audit event action `approve`, status transition, and actor id.
15. `test_admin_approve_reject_invalid_source_statuses_return_400`
   - Draft, approved, rejected, and locked statuses are rejected for approve/reject endpoints as appropriate.
16. `test_admin_rejects_submitted_timesheet_with_required_reason`
   - Submitted → rejected.
   - Assert non-empty reason is stored on the audit event.
17. `test_admin_reject_requires_reason`
   - Missing/blank reason returns HTTP 400 and keeps status submitted.

### Bulk approval
18. `test_admin_bulk_approve_all_submitted_timesheets`
   - Approve multiple submitted timesheets in one request.
   - Assert response includes approved ids and all statuses are approved.
19. `test_admin_bulk_approve_is_atomic_when_any_id_invalid`
   - Mix submitted and draft/missing/duplicate ids.
   - Assert HTTP 400 and all originally submitted rows remain submitted.
20. `test_admin_bulk_approve_requires_non_empty_ids`
   - Empty request is rejected with HTTP 400 or validation error.

### Audit endpoint
21. `test_admin_audit_endpoint_returns_oldest_to_newest_events`
   - Create/update/submit/approve or reject a timesheet.
   - Assert events are ordered by id/timestamp ascending and include actor/action/reason/status fields.
22. `test_admin_audit_endpoint_is_permission_protected`
   - Employee self-service user receives HTTP 403.

### CSV export
23. `test_admin_csv_export_uses_filters_and_safe_headers`
   - Export one period/status.
   - Assert fixed columns, scoped rows only, and content-disposition uses a server-generated filename.
24. `test_admin_csv_export_excludes_private_employee_fields`
   - Assert CSV text does not include IRD number, tax code, or pay rate.
25. `test_admin_csv_export_escapes_formula_like_notes_if_notes_included`
   - If note/description columns are exported, values beginning with `=`, `+`, `-`, or `@` are escaped to prevent spreadsheet formula execution.

### Regression coverage
26. `test_self_service_boundaries_still_hold_after_admin_routes`
   - Existing self-service list/detail/update/submit ownership tests remain green.
27. `test_core_lifecycle_rules_still_hold_after_admin_routes`
   - Existing service lifecycle tests remain green.

## Verification commands
Use the RTK wrapper for all shell verification:

```bash
rtk python -m pytest tests/test_timesheets_admin_routes.py
rtk python -m pytest tests/test_timesheets_self_service_routes.py tests/test_timesheets_service.py
rtk python -m pytest tests/test_employee_portal_auth.py tests/test_payroll_payslips.py
rtk python -m compileall app/routes app/services app/schemas tests
rtk git diff --check
```

## Security verification focus
- Confirm admin permissions are explicit and not inherited by employee self-service or payroll viewer users.
- Confirm all admin mutation endpoints record the authenticated actor id.
- Confirm no admin response/export leaks employee IRD number, tax code, pay rate, or payslip data.
- Confirm correction and bulk approval are tamper-resistant and audited.
- Confirm CSV output cannot be used as a formula-injection vector if free-text fields are included.

## Non-goals for this test spec
- Admin UI rendering tests.
- Pay-run import tests.
- `PayStub.timesheet_id` persistence tests.
- Pay-run processing lock tests.
- Project/client/task reporting tests.

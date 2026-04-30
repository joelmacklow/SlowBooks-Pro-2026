# Test Spec — Payroll Slice 3: employee self-service timesheet and payslip API

## Date
2026-04-30

## Objective
Prove that employee self-service timesheet and payslip APIs expose only the authenticated linked employee's records, preserve Slice 2 lifecycle rules, and do not leak payroll-private fields or cross-employee data.

## Target files
- New `tests/test_timesheets_self_service_routes.py`.
- Update `tests/test_payroll_payslips.py` for own-payslip route coverage.
- Existing supporting regressions: `tests/test_employee_portal_auth.py`, `tests/test_timesheets_service.py`, `tests/test_auth_rbac.py`, and `tests/test_auth_company_access_controls.py`.

## Test setup
- Reuse the in-memory master/company session split from `tests/test_employee_portal_auth.py:22-39` so auth links and company-local payroll/timesheet tables are both exercised.
- Use the owner bootstrap and employee user helper pattern from `tests/test_employee_portal_auth.py:41-105`.
- Seed company-local `Employee` rows directly or through existing employee route helpers, but never use employee-private fields as expected self-route response payload.
- Import `app.models` before `Base.metadata.create_all()` so `EmployeePortalLink`, `Timesheet`, `TimesheetLine`, `TimesheetAuditEvent`, `PayRun`, and `PayStub` tables exist.

## Required timesheet self-service tests
1. `test_employee_can_create_own_draft_timesheet_without_employee_id`
   - Linked employee user calls the self create route with period/lines only.
   - Assert persisted `Timesheet.employee_id` equals the resolved link employee.
   - Assert status is `draft`, total hours are calculated, and response omits payroll-private employee fields.

2. `test_self_list_returns_only_linked_employee_timesheets`
   - Seed timesheets for linked employee and another employee.
   - Call self list.
   - Assert only linked employee records are returned, ordered deterministically.

3. `test_self_detail_denies_other_employee_timesheet`
   - Linked employee requests another employee's `timesheet_id`.
   - Assert 404 or 403 and no foreign record fields in the error.

4. `test_self_create_rejects_or_ignores_spoofed_employee_id`
   - Submit a payload that attempts to include another `employee_id` if model parsing allows extra fields.
   - Assert the route either rejects the extra field or creates only for the resolved employee.

5. `test_self_update_own_draft_replaces_lines_and_audits`
   - Create linked employee draft.
   - Update lines through self route.
   - Assert total recalculates and an update audit event is written with the actor user id.

6. `test_self_update_denies_other_employee_even_if_draft`
   - Another employee's draft exists.
   - Linked employee attempts update.
   - Assert denial and unchanged lines/total.

7. `test_self_submit_own_draft_records_actor`
   - Linked employee submits own draft.
   - Assert status `submitted`, submitted timestamp exists, and audit event uses the employee user's id.

8. `test_self_cannot_edit_submitted_approved_or_locked_timesheet`
   - Submit own timesheet; assert update fails.
   - Admin/service approves and locks it; assert self update still fails.

9. `test_self_missing_or_inactive_link_is_rejected`
   - Employee role user without active link calls list/create/detail.
   - Assert failure without exposing unrelated employee/timesheet details.

10. `test_self_wrong_permission_cannot_create_or_submit`
    - Payroll viewer or staff user lacks `timesheets.self.create` / `timesheets.self.submit`.
    - Assert dependency failure for create/submit paths.

11. `test_self_csv_export_is_owned_and_safe`
    - Linked employee exports own timesheet CSV.
    - Assert `text/csv`, attachment filename is server-generated, headers are fixed, own lines are present, and private payroll fields are absent.

12. `test_self_csv_export_denies_other_employee_timesheet`
    - Linked employee attempts to export another employee's timesheet.
    - Assert denial and no CSV body with foreign data.

## Required own-payslip tests
1. `test_employee_can_list_own_processed_payslips`
   - Create two processed pay runs: one for linked employee, one for another employee.
   - Assert self list includes only linked employee's stubs with minimal run/stub fields.

2. `test_employee_can_download_own_processed_payslip_pdf`
   - Linked employee downloads own processed-run payslip.
   - Assert PDF response, safe `Content-Disposition`, and body includes the linked employee's name.

3. `test_employee_cannot_download_other_employee_payslip`
   - Linked employee attempts a processed run/stub belonging only to another employee.
   - Assert 404 or 403 and no other employee name in response.

4. `test_draft_pay_run_self_payslip_is_rejected`
   - Linked employee has a draft-run stub.
   - Assert own-payslip PDF route rejects until the run is processed, matching admin behavior.

5. `test_broad_admin_payslip_route_still_requires_admin_permission`
   - Employee self-service user cannot satisfy `payroll.payslips.view`.
   - The own-payslip route is guarded by `payroll.self.payslips.view`.
   - Existing admin route semantics remain unchanged.

## Regression tests to run
- `python -m pytest tests/test_timesheets_self_service_routes.py`
- `python -m pytest tests/test_payroll_payslips.py`
- `python -m pytest tests/test_employee_portal_auth.py tests/test_timesheets_service.py`
- `python -m pytest tests/test_auth_rbac.py tests/test_auth_company_access_controls.py`
- `python -m compileall app/routes app/services app/schemas tests`
- `git diff --check`

## Security assertions
- No self-service test should pass an authoritative `employee_id` to the route; ownership must come from the active auth context link resolved through `resolve_employee_link`.
- Negative coverage must include unauthenticated/wrong permission, missing link, inactive link if practical, wrong scope, other employee timesheet ID, other employee payslip/run ID, locked edits, and submitted edits.
- Timesheet list/detail/export responses must not include `ird_number`, `pay_rate`, `tax_code`, KiwiSaver, student loan, child-support, or payroll admin-only fields.
- Payslip list responses must not reuse full `PayRunResponse` because that can include stubs for other employees.
- Error messages should avoid confirming foreign employee names, pay rates, IRD numbers, or pay-run details.

## Manual smoke after implementation
1. Bootstrap owner.
2. Create two active employees.
3. Create and link one `employee_self_service` user to employee A.
4. Log in as employee A.
5. Create, update, list, detail, submit, and CSV export employee A's timesheet.
6. Attempt employee B's timesheet ID for detail/update/export and confirm denial.
7. Process a pay run containing employees A and B.
8. Download employee A's own payslip and confirm employee B's payslip is denied.

## Acceptance gate for Slice 4
- Targeted self-service route tests pass.
- Existing Slice 1 and Slice 2 regression tests pass.
- Auth/company-scope regression tests pass.
- `compileall` and `git diff --check` pass.
- Explicit security review finds no known cross-employee IDOR, permission escalation, CSV header/filename, or payroll-PII leak.

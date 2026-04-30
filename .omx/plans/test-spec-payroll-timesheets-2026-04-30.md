# Test Spec — Payroll timesheets and employee self-service

## Date
2026-04-30

## Strategy
This is a high-risk payroll/employee-data feature. Build it in test-first slices. Each implementation slice should add targeted backend tests before code changes, then frontend tests for rendering/permission behavior where UI is touched. Do not rely on manual QA for access-control boundaries.

## Global invariants to protect
1. Employee users can only access their own linked employee/timesheet/pay records and payslips for the active company scope.
2. Payroll admins with explicit permissions can manage timesheets across employees.
3. Approved/locked/processed payroll source data cannot be silently mutated.
4. Timesheet totals are deterministic and use consistent decimal rounding.
5. Existing NZ payroll calculations continue to use `calculate_payroll_stub` and existing pay-run totals remain compatible.
6. Sensitive payroll data is not exposed through unauthorised routes, exports, logs, or frontend state.

## Slice 1 — Employee identity linkage and RBAC foundation
### Tests to add first
- Creating/linking an employee portal user requires `users.manage` or a dedicated employee-user management permission.
- A linked employee user receives only self-service permissions.
- An employee user cannot call `employees.view_private`, `payroll.view`, or admin-only timesheet routes.
- Employee self-context resolves the expected `employee_id` for the active company scope.
- Link resolution does not assume a cross-database FK from master auth records into company-scoped `employees`.
- Cross-company, inactive, duplicate-active, and stale employee links are rejected.

### Verification
- Targeted auth tests, likely in `tests/test_auth_rbac.py` or a new `tests/test_employee_portal_auth.py`.
- `git diff --check`.

## Slice 2 — Timesheet core model/service
### Tests to add first
- Draft timesheet can be created for an employee and period.
- Duplicate active timesheets for the same employee/period are prevented.
- Duration-mode lines sum total hours correctly.
- Start/end/break lines calculate hours correctly.
- Invalid ranges, negative hours, and breaks longer than shift are rejected.
- Status transitions enforce allowed lifecycle only:
  - draft -> submitted
  - submitted -> approved/rejected
  - rejected -> draft/submitted after correction
  - approved -> locked when imported/processed
- Audit events are created for create, update, submit, approve, reject, and lock.

### Verification
- New `tests/test_timesheets_service.py`.
- Targeted model/schema tests if migrations/model setup require it.

## Slice 3 — Employee self-service API
### Tests to add first
- Employee can list only own timesheets.
- Employee can create/update own draft timesheet.
- Employee cannot spoof another `employee_id` in payload.
- Employee cannot edit submitted/approved/locked timesheets.
- Employee can submit a valid draft.
- Employee can export/print only own timesheet.
- Employee can list/download only their own processed payslips through self-service routes.
- Employee cannot access another employee's payslip by guessing `run_id` or `employee_id`.
- Self-service payslip access does not require or imply broad `payroll.payslips.view`.
- Unauthenticated access returns 401; wrong employee returns 403 or 404 consistently.

### Verification
- New `tests/test_timesheets_self_routes.py`.
- Include negative access-control tests for every route.

## Slice 4 — Admin review API
### Tests to add first
- Admin can list pay-run/period readiness grouped by status.
- Admin can view submitted timesheet detail.
- Admin can correct submitted timesheet with audit reason.
- Admin can approve, reject with reason, and bulk approve.
- Admin cannot approve invalid totals or already locked timesheets.
- Viewer/non-admin payroll roles cannot approve or export unless permissioned.
- Admin CSV export is scoped and filename/header safe.

### Verification
- New `tests/test_timesheets_admin_routes.py`.
- Negative RBAC tests in auth route coverage.

## Slice 5 — Payroll integration
### Tests to add first
- Draft pay run imports approved hourly timesheet totals into `PayStub.hours`.
- Missing/unapproved hourly timesheets are reported before processing.
- Approved-hours lookup/import and lock-on-process behavior are covered at the payroll-timesheet integration service seam, not only through route tests.
- Manual-hours override, if retained, requires explicit admin permission/path and is audited.
- Processing a pay run locks linked source timesheets.
- Processed pay-run totals match existing NZ payroll expected values for hourly employees.
- Existing salary employee pay-run behavior is unchanged.
- Payslip and payday filing exports continue to work with source-timesheet stubs.

### Verification
- Extend `tests/test_nz_payroll_runs.py` or add `tests/test_payroll_timesheet_integration.py`; prefer service-level tests for `app/services/payroll_timesheet_integration.py` plus route smoke coverage.
- Run existing payroll tests after targeted changes.

## Slice 6 — Employee UI
### Tests to add first
- Employee route renders only self-service navigation and timesheet list.
- Draft entry supports total-hours and start/end/break modes.
- Submit action calls the self endpoint.
- Rejected status displays reason and allows correction.
- Approved/locked status disables editing.
- Employee cannot see admin controls in DOM/rendered state.

### Verification
- New JS tests under `tests/js_*timesheet*.test.js`.
- Manual smoke for light/dark/mobile-width layout.

## Slice 7 — Admin UI
### Tests to add first
- Payroll admin dashboard groups timesheets by readiness status.
- Approve/reject/correct actions call admin endpoints and refresh state.
- Payroll page shows approved-timesheet import/readiness state.
- Users without timesheet admin permissions do not see approval controls.

### Verification
- JS admin payroll/timesheet tests.
- Manual smoke of the pay-run creation path.

## Slice 8 — Project/client/task reporting
### Tests to add first
- Optional project/client/task metadata can be saved and exported.
- Summary reports aggregate by employee/project/client/task for selected period.
- Employee users do not see other employees' project time.
- Empty metadata does not break payroll import.

### Verification
- Route/service tests plus focused JS reporting tests if UI is added.

## Slice 9 — Hardening and compliance pass
### Tests/checks
- Full negative access-control matrix for employee/admin timesheet endpoints.
- Export path/header safety tests.
- Audit event integrity tests for locked records.
- Sensitive logging review: no raw tokens, payroll PII, or full export payloads in logs.
- Retention/read path review against NZ wage/time record requirements.

## Safety command set per slice
Use the smallest targeted checks first, then broaden before commit:
- Targeted Python test file for the slice.
- Targeted JS test file when UI changes.
- Existing payroll regression tests touched by the slice.
- `npm test -- <target>` where applicable.
- `npm run lint` if frontend files are touched and script is available.
- `npm run typecheck` if applicable to changed JS/TS surface.
- `git diff --check`.

## Manual acceptance smoke before final feature PR
- Create employee and linked self-service user.
- Employee logs in, creates a daily-hours timesheet, submits.
- Employee logs in, creates a start/end/break timesheet, submits.
- Payroll admin rejects one timesheet; employee corrects and resubmits.
- Payroll admin approves timesheet.
- Payroll admin creates draft pay run and imports approved hours.
- Process pay run; linked timesheet becomes locked.
- Employee can view/export own approved/locked timesheet and cannot edit it.
- Employee cannot access another employee's timesheet by ID.
- Employee cannot access another employee's payslip PDF or pay-stub listing by ID.

## Non-goals for testing in MVP
- Native mobile app automation.
- Leave/expense workflows.
- GPS/location tracking.
- Third-party integration tests.

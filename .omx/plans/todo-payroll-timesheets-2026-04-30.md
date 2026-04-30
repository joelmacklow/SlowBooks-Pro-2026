# Todo — Payroll timesheets multi-session backlog

## Status legend
- `[ ]` not started
- `[~]` in progress
- `[x]` complete
- `[!]` blocked / needs decision

## Operating notes
- This is a significant payroll/PII feature. Keep each todo slice on a task-scoped branch and commit/push after verification.
- Before implementing any slice, keep the PRD and test spec updated if scope changes.
- Use test-first development for behavior and access-control changes.
- Perform explicit security review for every slice touching employee/payroll data.
- Do not merge employee self-service without negative tests proving cross-employee access is blocked.

## Slice 0 — Planning artifacts
- [x] Create PRD: `.omx/plans/prd-payroll-timesheets-2026-04-30.md`.
- [x] Create test spec: `.omx/plans/test-spec-payroll-timesheets-2026-04-30.md`.
- [x] Create multi-session todo: `.omx/plans/todo-payroll-timesheets-2026-04-30.md`.
- [x] Revisit graph-backed plan changes before implementation: period-keyed MVP, master-side employee link, own-payslip self routes, and payroll integration service seam.
- [ ] Revisit remaining open decisions before implementation as needed: overnight shifts, salary exceptions, project metadata shape, invite flow.

## Slice 1 — Employee identity linkage and RBAC foundation
- [x] Add/extend plan and test spec if employee identity design changes: `.omx/plans/prd-payroll-employee-identity-rbac-2026-04-30.md` and `.omx/plans/test-spec-payroll-employee-identity-rbac-2026-04-30.md`.
- [ ] Add tests for employee-user link creation, inactive links, company scope isolation, stale employee IDs, and duplicate active link prevention.
- [ ] Add tests for employee role permissions and forbidden payroll/admin access.
- [ ] Implement master auth-side employee-user link model/service/schema with `company_scope` and company-local `employee_id`.
- [ ] Avoid assuming a cross-database FK from auth/master records into company-scoped employee tables.
- [ ] Add self-service permissions and employee role in `app/services/auth.py`, including own payslip view permission if delivered in Slice 3.
- [ ] Add helper to resolve authenticated user's linked employee for active company scope.
- [ ] Add admin API for link/unlink/invite or account creation path.
- [ ] Run targeted auth tests and `git diff --check`.
- [ ] Security review: cross-company access, inactive users, permission escalation, sensitive logging.
- [ ] Lore commit and push branch.

## Slice 2 — Timesheet core model/service
- [ ] Add tests for draft creation, duplicate prevention, lifecycle transitions, totals, invalid ranges, and audit events.
- [ ] Implement `Timesheet`, `TimesheetLine`, and `TimesheetAuditEvent` models.
- [ ] Add schemas for timesheet detail/list/upsert/status actions.
- [ ] Implement service functions for create/update/submit/approve/reject/lock.
- [ ] Implement total-hour calculation for duration mode.
- [ ] Implement total-hour calculation for start/end/break mode.
- [ ] Define decimal rounding and validation rules.
- [ ] Run targeted service/model tests and `git diff --check`.
- [ ] Security review: tamper resistance, audit integrity, payroll PII fields.
- [ ] Lore commit and push branch.

## Slice 3 — Employee self-service API
- [ ] Add route tests for own timesheet list/detail/create/update/submit/export.
- [ ] Add negative tests for spoofed `employee_id`, cross-employee ID access, unauthenticated access, and locked edits.
- [ ] Add tests for own payslip list/PDF access and cross-employee payslip denial.
- [ ] Implement `app/routes/timesheets.py` self endpoints.
- [ ] Register route in `app/main.py`.
- [ ] Add employee self-service payslip route(s) that verify the active employee link instead of granting broad payroll permissions.
- [ ] Ensure self routes never trust client-supplied employee ownership.
- [ ] Add simple own-timesheet CSV/print export.
- [ ] Run targeted route tests and `git diff --check`.
- [ ] Security review: IDOR, export scoping, sensitive response shape.
- [ ] Lore commit and push branch.

## Slice 4 — Admin review API
- [ ] Add admin route tests for readiness list, detail, correction, approve, reject, bulk approve, audit, CSV export.
- [ ] Add negative permission tests for payroll viewers and employee users.
- [ ] Implement admin timesheet endpoints.
- [ ] Add pay-period/pay-run grouping and missing-timesheet detection.
- [ ] Add correction-with-reason audit events.
- [ ] Add admin CSV export with safe filename/header handling.
- [ ] Run targeted admin route tests and `git diff --check`.
- [ ] Security review: broad payroll access, export scope, audit completeness.
- [ ] Lore commit and push branch.

## Slice 5 — Payroll integration
- [ ] Add tests for approved-hours import into draft pay runs.
- [ ] Add tests for missing/unapproved timesheet warnings or blockers.
- [ ] Add tests for manual override path if retained.
- [ ] Add tests that pay-run processing locks linked timesheets.
- [ ] Add `timesheet_id` linkage to pay stubs if needed.
- [ ] Add `app/services/payroll_timesheet_integration.py` or equivalent service seam for readiness, import, and locking.
- [ ] Extend payroll creation/preview to consume approved timesheets through the service seam without bloating payroll route functions.
- [ ] Preserve existing salary employee payroll behavior.
- [ ] Verify payday filing and payslip paths still work.
- [ ] Run payroll regression tests and `git diff --check`.
- [ ] Security review: payroll source tampering, locked record edits, auditability.
- [ ] Lore commit and push branch.

## Slice 6 — Employee UI
- [ ] Add JS tests for employee route rendering and permission-limited navigation.
- [ ] Add employee timesheet list/detail form.
- [ ] Support total-hours entry UI.
- [ ] Support start/end/break entry UI with calculated totals.
- [ ] Add draft save, submit, rejected correction, approved/locked read-only states.
- [ ] Add own export/print action.
- [ ] Validate light/dark and narrow viewport behavior.
- [ ] Run targeted JS tests and `git diff --check`.
- [ ] Security review: hidden admin controls, exposed employee IDs, frontend-only assumptions.
- [ ] Lore commit and push branch.

## Slice 7 — Admin UI
- [ ] Add JS tests for admin timesheet dashboard status grouping.
- [ ] Add admin review dashboard/page.
- [ ] Add approve/reject/correct/audit UI.
- [ ] Add payroll pay-run readiness/import controls.
- [ ] Hide admin controls from users without permissions.
- [ ] Validate light/dark and empty states.
- [ ] Run targeted JS tests and `git diff --check`.
- [ ] Security review: UI route guards and backend-backed permissions.
- [ ] Lore commit and push branch.

## Slice 8 — Project/client/task tracking and reports
- [ ] Decide whether project/client/task fields reference existing tables or remain metadata initially.
- [ ] Add tests for metadata save/export/reporting.
- [ ] Implement optional metadata fields in API/UI.
- [ ] Add report summaries by employee/project/client/task.
- [ ] Ensure metadata is optional and does not block payroll import.
- [ ] Run targeted reporting tests and `git diff --check`.
- [ ] Security review: report scoping and employee privacy.
- [ ] Lore commit and push branch.

## Slice 9 — Compliance and hardening pass
- [ ] Run full timesheet access-control matrix.
- [ ] Review retention expectations against NZ wage/time record requirements.
- [ ] Confirm audit events exist for every lifecycle mutation.
- [ ] Confirm locked records cannot be edited through API or UI.
- [ ] Confirm exports are scoped and safe.
- [ ] Confirm no sensitive payroll data is logged unexpectedly.
- [ ] Run broader payroll/auth/frontend regression suite.
- [ ] Document final manual smoke results.
- [ ] Lore commit and push branch.

## Future follow-ups after MVP
- [ ] Leave request integration.
- [ ] Expense claim integration.
- [ ] Roster/schedule comparison.
- [ ] Native mobile app or PWA polish.
- [ ] Third-party time app integration points.
- [ ] Advanced project budget and quote/estimate analysis.

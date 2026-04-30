# PRD: Payroll timesheet admin review API slice

## Objective
Deliver the next payroll-timesheets implementation slice by exposing a backend-only payroll-admin review API for submitted employee timesheets: period readiness, detail, correction-with-reason, approve/reject, bulk approval, audit visibility, and CSV export.

This slice intentionally stops before payroll pay-run import and admin UI work. It creates the API surface that later payroll integration and UI slices can call without growing `app/routes/payroll.py`.

## Current-state evidence
- The timesheet router is already registered in `app/main.py:41` and `app/main.py:126`.
- `app/routes/timesheets.py:33-154` currently exposes only employee self-service list/create/detail/update/submit/CSV endpoints.
- Self-service routes resolve the active employee link server-side via `_resolved_employee_id` in `app/routes/timesheets.py:28-30` and never accept client-supplied ownership for self-create in `app/routes/timesheets.py:56-75`.
- Core lifecycle services already exist: `approve_timesheet` in `app/services/timesheets.py:336-353`, `reject_timesheet` in `app/services/timesheets.py:356-383`, and `lock_timesheet` in `app/services/timesheets.py:386-403`.
- The durable status model is `draft`, `submitted`, `approved`, `rejected`, `locked` in `app/models/timesheets.py:22-27`.
- Timesheet records are company-local, employee/period-unique, and already relate to company-local employees and pay runs in `app/models/timesheets.py:51-75`.
- Audit rows store actor, action, old/new status, reason, and timestamp in `app/models/timesheets.py:95-107`.
- Current permissions define only employee self-service timesheet capabilities in `app/services/auth.py:50-52`; `payroll_admin` has payroll permissions in `app/services/auth.py:104-117` but no explicit admin timesheet permissions yet.
- Existing self-service route tests in `tests/test_timesheets_self_service_routes.py:132-435` provide reusable fixtures and negative ownership patterns for the admin route tests.
- Code-review graph entrypoint before planning reported 3,340 nodes, 33,087 edges, and high-risk auth/payroll flows (`bootstrap_admin`, `login`, `create_user`), so this slice keeps route orchestration thin and permission changes explicit.

## Requirements summary
1. Payroll admins can review timesheets across employees for the active company database.
2. Admin review is period-first: a readiness endpoint reports active hourly employees as `not_started`, `draft`, `submitted`, `approved`, `rejected`, or `locked` for a requested period.
3. Admin detail/audit endpoints expose timesheet lifecycle data but not payroll-private employee fields such as IRD number, tax code, or pay rate.
4. Admin correction requires a non-empty reason, recalculates totals, and writes a correction audit event.
5. Approval/rejection endpoints use the existing service lifecycle rules and record the authenticated actor.
6. Bulk approval validates the whole request before mutating so one invalid/non-submitted timesheet does not partially approve the batch.
7. CSV export is scoped by server-side filters and uses safe server-generated headers/filenames.
8. Employee self-service users and payroll viewers cannot access admin review, correction, approval, bulk approval, audit, or export endpoints.

## Constraints
- High-risk payroll/PII slice: tests first, targeted verification, and explicit security review before commit/push.
- No new dependencies.
- Backend/API only: no admin UI, no employee UI changes, no pay-run import, no `PayStub.timesheet_id` linkage, and no pay-run processing lock changes.
- Do not grant admin timesheet operations through broad self-service permissions.
- Do not serialize `Employee` ORM objects directly from admin responses.
- Keep `app/routes/payroll.py` untouched except for verification; payroll integration belongs in Slice 5.
- Keep correction conservative: corrections are allowed only before payroll lock. Approved/locked timesheets must not be silently edited in this slice; if an approved timesheet needs correction, use a later explicit reversal/reopen workflow rather than mutating approved payroll source data.

## Implementation sketch
1. **Tests first**
   - Add `tests/test_timesheets_admin_routes.py`, reusing the in-memory master/company database style from `tests/test_timesheets_self_service_routes.py:23-119`.
   - Cover readiness, filters, detail privacy, correction audit, approve/reject, bulk approve atomicity, audit ordering, CSV safety, and permission negatives before implementation.
2. **Admin permissions**
   - Extend `PERMISSION_DEFINITIONS` in `app/services/auth.py:22-63` with:
     - `timesheets.manage`
     - `timesheets.approve`
     - `timesheets.export`
   - Add those permissions to `payroll_admin` in `app/services/auth.py:104-117`.
   - Do not add them to `payroll_viewer` or `employee_self_service`.
3. **Schemas**
   - Extend `app/schemas/timesheets.py` with admin-safe response/request models:
     - employee summary with `employee_id` and display name only;
     - readiness row;
     - admin list/detail responses;
     - correction request requiring `lines` and `reason`;
     - bulk approve request/response;
     - export/filter query-compatible status validation.
4. **Service helpers**
   - Extend `app/services/timesheets.py` with route-neutral helpers:
     - list/filter all company timesheets by period/status/employee;
     - detail lookup by id;
     - period readiness for active hourly employees;
     - correction with required reason, total recalculation, and audit event;
     - bulk approve with pre-validation.
   - Reuse `_build_line_models`, `_coerce_status`, `_status_value`, `_add_audit_event`, and lifecycle functions rather than duplicating transition logic.
5. **Routes**
   - Add admin routes under the existing router in `app/routes/timesheets.py` using an `/admin/...` prefix so they do not conflict with `/self/...`:
     - `GET /api/timesheets/admin/readiness`
     - `GET /api/timesheets/admin/export`
     - `POST /api/timesheets/admin/bulk-approve`
     - `GET /api/timesheets/admin`
     - `GET /api/timesheets/admin/{timesheet_id}`
     - `PUT /api/timesheets/admin/{timesheet_id}/correction`
     - `POST /api/timesheets/admin/{timesheet_id}/approve`
     - `POST /api/timesheets/admin/{timesheet_id}/reject`
     - `GET /api/timesheets/admin/{timesheet_id}/audit`
   - Register fixed static paths such as `/admin/export` and `/admin/bulk-approve` before `/admin/{timesheet_id}` so Starlette/FastAPI route matching cannot treat those words as ids.
   - Map service `ValueError` failures to 400/404 consistently with the self routes in `app/routes/timesheets.py:51-52` and `app/routes/timesheets.py:128-131`.
6. **CSV safety**
   - Generate admin CSV server-side with fixed columns, no formulas, no client-controlled filename, and a `Content-Disposition` filename derived from validated period/filter values.

## Impacted files and likely blast radius
- `app/services/auth.py` — add explicit admin timesheet permissions to definitions and payroll admin role only.
- `app/schemas/timesheets.py` — add admin request/response contracts.
- `app/services/timesheets.py` — add admin list/readiness/correction/bulk/export helpers.
- `app/routes/timesheets.py` — add admin review endpoints; keep existing self endpoints stable.
- `tests/test_timesheets_admin_routes.py` — new route/service regression tests.
- Optional verification-only files: `tests/test_timesheets_self_service_routes.py`, `tests/test_timesheets_service.py`, and payroll tests.

No schema migration should be needed for this slice because `Timesheet`, `TimesheetLine`, and `TimesheetAuditEvent` already exist.

## Acceptance criteria
1. A payroll admin can request period readiness and see one row per active hourly employee with accurate status and timesheet id where present.
2. Readiness marks missing active hourly employee timesheets as `not_started`.
3. Admin list/detail endpoints support period/status/employee filters and return admin-safe timesheet data.
4. Admin responses do not include IRD numbers, tax codes, pay rates, or full `Employee` objects.
5. Admin correction of a draft/rejected/submitted timesheet replaces lines, recalculates `total_hours`, requires a reason, preserves/sets a review-safe status, and writes a correction audit event with actor id and reason.
6. Approved and locked timesheets cannot be corrected by this slice.
7. Admin approval accepts only submitted timesheets and writes an approve audit event.
8. Admin rejection accepts only submitted timesheets, requires a non-empty reason, and writes a reject audit event.
9. Bulk approval approves all requested submitted timesheets or none when any requested id is invalid, not submitted, or duplicated.
10. Audit endpoint returns events ordered oldest-to-newest and is admin-permission protected.
11. Admin CSV export is filtered, has safe fixed headers, and excludes payroll-private fields.
12. Employee self-service users, payroll viewers, and unauthenticated callers cannot use admin review endpoints.
13. Existing self-service timesheet route tests and core timesheet service tests still pass.

## Test plan
Run tests with the RTK command wrapper:

1. Targeted new suite:
   - `rtk python -m pytest tests/test_timesheets_admin_routes.py`
2. Regression suites:
   - `rtk python -m pytest tests/test_timesheets_self_service_routes.py tests/test_timesheets_service.py`
   - `rtk python -m pytest tests/test_employee_portal_auth.py tests/test_payroll_payslips.py`
3. Syntax/compile:
   - `rtk python -m compileall app/routes app/services app/schemas tests`
4. Safety:
   - `rtk git diff --check`

## Security review checklist
- **Auth/RBAC:** every admin endpoint requires `timesheets.manage`, `timesheets.approve`, or `timesheets.export`; self-service and payroll-viewer roles remain denied.
- **IDOR:** admin endpoints operate only inside the active company DB; self endpoints remain employee-link scoped.
- **PII minimization:** no IRD number, pay rate, tax code, private employee profile, or payslip data in admin timesheet responses/exports.
- **Tamper resistance:** correction is explicit, reasoned, audited, and blocked for approved/locked records.
- **Bulk mutation safety:** validate all ids/statuses before approving any row.
- **CSV injection/header safety:** fixed columns, no user-controlled filename, and formula-like cell values escaped if free-text notes are included.
- **Sensitive logging:** no new logging of payroll or employee-private fields.
- **Shell/filesystem/SSRF/deserialization:** no new shell, filesystem write, outbound request, or unsafe deserialization surface.
- **Dependency risk:** no new dependency.

## Risks and mitigations
- **High — payroll source tampering:** block approved/locked corrections; require reasons/audit for all admin corrections.
- **High — permission broadening:** introduce explicit timesheet admin permissions and assign only to `payroll_admin`/owner via `set(PERMISSION_DEFINITIONS.keys())`.
- **Medium — bulk partial updates:** pre-validate all requested timesheets before mutation; test invalid batch leaves statuses unchanged.
- **Medium — PII leakage in admin responses:** use dedicated schemas and tests asserting private fields are absent.
- **Medium — route ordering conflicts:** place fixed `/admin/...` routes before any parameterized admin route and keep `/self/...` routes unchanged.

## Out of scope
- Admin UI dashboard.
- Payroll pay-run import/readiness controls in `app/routes/payroll.py`.
- `PayStub.timesheet_id` linkage and locking on pay-run processing.
- Project/client/task metadata.
- Reopen/reversal workflow for approved timesheets.

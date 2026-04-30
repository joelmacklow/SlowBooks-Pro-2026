# PRD: Payroll timesheet core model/service slice

## Objective
Deliver the next payroll-timesheets implementation slice by adding the company-local timesheet data model, schemas, and service lifecycle needed before employee self-service or admin review routes are exposed.

## Requirements summary
- Parent feature plan: `.omx/plans/prd-payroll-timesheets-2026-04-30.md`.
- Parent test spec: `.omx/plans/test-spec-payroll-timesheets-2026-04-30.md`.
- Parent todo: `.omx/plans/todo-payroll-timesheets-2026-04-30.md`.
- Slice 1 has established master/auth-side employee links; this slice stays in the company database and stores `employee_id` against the local `employees` table rather than linking to auth users.
- Existing company-local payroll tables are `Employee`, `PayRun`, and `PayStub` in `app/models/payroll.py:30-113`; `PayStub.hours` remains the final payroll input/output for now.
- Existing payroll calculations already round money in `app/services/nz_payroll.py:14-23` and calculate hourly gross from `Employee.pay_rate * hours` in `app/services/nz_payroll.py:151-154`; this slice should not duplicate PAYE/pay-run math.
- Employee-portal link resolution exists in `app/services/employee_portal.py:185-205`; future self-service routes will use it, but this slice should not expose routes.
- Current app router registration lives in `app/main.py:24-42` and `app/main.py:121-125`; no timesheet router should be added until Slice 3.

## Constraints
- High-risk payroll/PII slice: write tests first and perform an explicit security review before commit/push.
- Keep scope backend-only: no employee routes, admin routes, UI, export, payslip access, or payroll pay-run import in this slice.
- Do not add dependencies.
- Keep orchestration in `app/services/timesheets.py`; route files must remain untouched except in later slices.
- Do not add cross-database foreign keys to master/auth records. `TimesheetAuditEvent.actor_user_id` may store the auth user id as an integer only.
- Use period-keyed timesheets (`period_start`, `period_end`) before pay-run linkage; any nullable `pay_run_id` must remain unpopulated until the payroll integration slice.
- MVP rejects overnight shifts explicitly until the open decision is resolved.

## Implementation sketch
1. Add tests first in `tests/test_timesheets_service.py`.
2. Add `app/models/timesheets.py` with:
   - `TimesheetStatus`: `draft`, `submitted`, `approved`, `rejected`, `locked`.
   - `TimesheetEntryMode`: `duration`, `start_end`.
   - `Timesheet`: `employee_id`, optional `pay_run_id`, `period_start`, `period_end`, `status`, `total_hours`, lifecycle timestamps, `created_at`, `updated_at`.
   - `TimesheetLine`: `timesheet_id`, `work_date`, `entry_mode`, `duration_hours`, `start_time`, `end_time`, `break_minutes`, `notes`.
   - `TimesheetAuditEvent`: `timesheet_id`, optional `timesheet_line_id`, `actor_user_id`, `action`, `status_from`, `status_to`, `reason`, minimal metadata text/JSON, `created_at`.
3. Add Alembic migration for the three tables plus indexes/constraints:
   - unique employee/period guard for duplicate prevention;
   - indexes for employee/period/status lookups;
   - foreign keys to company-local `employees`, `pay_runs`, and timesheet tables only.
4. Register models in `app/models/__init__.py` so `Base.metadata.create_all()` test setup sees them.
5. Add `app/schemas/timesheets.py` for service and future route contracts:
   - line upsert input;
   - create/update request;
   - detail/list response;
   - status action request with optional reason.
6. Add `app/services/timesheets.py` lifecycle helpers:
   - `create_timesheet`, `update_timesheet`, `submit_timesheet`, `approve_timesheet`, `reject_timesheet`, `lock_timesheet`;
   - total-hours calculation for duration mode and same-day start/end/break mode;
   - Decimal hour normalization to `0.01` using `ROUND_HALF_UP`;
   - lifecycle transition validation and audit-event creation.
7. Keep future payroll integration thin by exposing service functions that return persisted `total_hours`, not payroll-calculated amounts.

## Impacted files and blast radius
- New `app/models/timesheets.py` — primary company-local timesheet tables.
- New Alembic migration under `alembic/versions/`.
- `app/models/__init__.py` — model registration only.
- New `app/schemas/timesheets.py` — Pydantic contracts for the service and future routes.
- New `app/services/timesheets.py` — lifecycle, validation, totals, and audit.
- New `tests/test_timesheets_service.py` — model/service regression tests.
- No expected changes to `app/routes/payroll.py`, `app/routes/employee_portal.py`, `app/main.py`, or frontend assets in this slice.

Code-review graph context before planning: 3,340 nodes / 33,087 edges across 373 files; current branch diff risk is high because payroll/auth work affects bootstrap/login/create-user flows, so this slice deliberately avoids route/auth changes and keeps the blast radius to model/service tests.

## Acceptance criteria
1. A draft timesheet can be created for an active employee and explicit period with one or more valid lines.
2. Duplicate timesheets for the same employee/period are rejected before database commit and protected by a database constraint.
3. Duration-mode lines calculate decimal hours to two places.
4. Start/end/break-mode lines calculate same-day decimal hours to two places.
5. Invalid periods, work dates outside the period, negative duration, zero/negative net hours, break longer than the shift, and overnight shifts are rejected with clear errors.
6. Only draft or rejected timesheets can be updated by the core service; updating a rejected timesheet returns it to draft for resubmission.
7. Lifecycle transitions are enforced: draft/rejected → submitted, submitted → approved/rejected, approved → locked.
8. Approved, submitted, and locked timesheets cannot be silently edited.
9. Every create/update/submit/approve/reject/lock mutation writes an audit event with actor id, action, old/new status where relevant, and reason when required.
10. Rejection requires a non-empty reason.
11. Timesheet responses do not include IRD numbers, pay rates, tax codes, or other payroll-private employee fields.
12. Existing NZ payroll model/run tests still pass.

## Test plan
- Add `tests/test_timesheets_service.py` covering the cases in `.omx/plans/test-spec-payroll-timesheet-core-model-service-2026-04-30.md`.
- Run targeted tests first:
  - `python -m pytest tests/test_timesheets_service.py`
  - `python -m pytest tests/test_nz_payroll_data_model.py tests/test_nz_payroll_runs.py`
- Run safety checks:
  - `python -m compileall app/models app/schemas app/services tests`
  - `git diff --check`

## Security review checklist
- Auth boundary: no routes are added, and no broad payroll/admin permission is introduced.
- PII: schemas/responses must not serialize full `Employee` records or payroll-private fields.
- Tamper resistance: service blocks edits after submit/approve/lock except through explicit lifecycle actions.
- Audit integrity: every mutation creates a durable audit event before commit.
- Filesystem/shell/SSRF/deserialization: no new file, shell, outbound request, or unsafe deserialization surface.
- Dependency risk: no new dependency.

## Risk notes
- **High — payroll record tampering:** mitigated by strict transitions, locked status, and audit events.
- **High — later IDOR risk:** deferred routes must use `resolve_employee_link`; this slice avoids self-service route exposure.
- **Medium — rounding disagreement:** define hours rounding in tests now so later payroll integration imports stable totals.
- **Medium — period/pay-run mismatch:** keep timesheets period-keyed and avoid pay-run import behavior until Slice 5.
- **Medium — overnight shifts:** explicitly reject in MVP rather than guessing policy.

## Out of scope
- Employee self-service routes, payslip routes, CSV/print export, admin review routes, bulk approval, payroll import, UI, project/client/task metadata, and final compliance hardening.

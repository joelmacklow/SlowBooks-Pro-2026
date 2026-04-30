# PRD — Payroll timesheets and employee self-service

## Date
2026-04-30

## Objective
Add a payroll timesheeting feature so employees can log in, enter their own timesheets for each pay period/pay run, submit them for approval, and have approved hours flow into NZ payroll pay runs with secure employee-only access and auditable admin review.

## Background and current-state evidence
- SlowBooks already has NZ payroll models for `Employee`, `PayRun`, and `PayStub` in `app/models/payroll.py`.
- Payroll pay-run creation currently accepts manual hourly `hours` input and calculates PAYE through `app/routes/payroll.py` and `app/services/nz_payroll.py`.
- Payroll UI exists in `app/static/js/payroll.js`, including manual hourly inputs for draft pay runs.
- Auth/RBAC exists in `app/routes/auth.py` and `app/services/auth.py`, with payroll/admin permissions but no employee self-service identity linkage.
- No durable timesheet model or employee portal workflow currently exists; `PayStub.hours` is only the final payroll input/output.
- Code-review graph was rebuilt before this plan review: 373 files, 3,340 nodes, 33,087 edges, and 212 affected flows across the projected auth/payroll/timesheet integration surface. The graph shows the highest-risk existing hotspots are `app/routes/payroll.py::process_pay_run`, `app/routes/payroll.py::create_pay_run`, and `app/static/js/payroll.js::render`, so implementation should keep route/UI changes thin and move orchestration into services.

## External product reference
Xero's payroll timesheet page describes a self-service model where employees submit timesheets digitally, admins review and approve them, approved time is included in pay runs, and employees can use phone/tablet/desktop while only accessing their own pay records. It also highlights automatic hour totals, total-hours or start/end-time entry, admin corrections before approval, employee copies/export/print, project/client time tracking, and reporting for project/productivity insights.

Reference: https://www.xero.com/nz/accounting-software/payroll/timesheet/

## NZ compliance reference
Employment New Zealand states employers must keep wages/time records and holiday/leave records for 6 years. Timesheet records should therefore be retained securely, auditable, and retrievable by authorised users.

Reference: https://www.employment.govt.nz/starting-employment/rights-and-responsibilities/record-keeping

## Problem
Hourly payroll currently relies on payroll admins manually entering hours during pay-run creation. That creates unnecessary admin work, weakens the audit trail for wage/time records, and prevents employees from validating their own hours before payroll is processed. A significant feature is needed rather than a small field addition: self-service login, timesheet lifecycle, approvals, audit history, payroll integration, and privacy controls must work together.

## Users and jobs-to-be-done
- **Employee**: enter hours quickly, save drafts, submit for a pay period, see status, correct rejected entries, and retain access to their own submitted/approved timesheets.
- **Payroll admin**: monitor missing/submitted timesheets for a pay run, correct errors with an audit trail, approve/reject, and import approved hours into payroll.
- **Business owner/manager**: see payroll readiness, project/client time summaries, and reliable records for compliance or disputes.
- **Future accountant/bookkeeper**: review approved wage/time records without exposing unrelated employee data.

## Scope
### In scope for the full feature
1. Employee self-service account linkage to payroll employee records.
2. Employee timesheet list/detail/create/edit/submit flows.
3. Timesheet lifecycle: `draft`, `submitted`, `approved`, `rejected`, `locked`, `void`.
4. Line-level time entry with both total-hours mode and start/end/break mode.
5. Admin review dashboard by pay period/pay run.
6. Admin approve/reject/correct workflow with audit events.
7. Approved timesheet import into draft pay runs for hourly employees.
8. Locking approved/source timesheets once a pay run is processed.
9. Employee-only access to own timesheets and payslips.
10. Employee export/print of their own timesheets.
11. Optional project/client/task fields for future project reporting.
12. CSV/reporting surfaces for payroll/admin compliance review.

### Out of scope for MVP, but planned later
- Native mobile app.
- Leave requests.
- Expense claims.
- Rostering/scheduling.
- GPS/location capture.
- Third-party app integrations.
- Advanced project budget and quote-estimate analytics beyond storing project/task metadata.

## Proposed UX
### Employee portal
- New employee landing page after login with cards for current/open timesheet period, submitted/approved/rejected status, and recent payslips.
- Timesheet entry supports daily total hours; start time, end time, break minutes, and auto-calculated hours; notes per line; and optional project/client/task selection when enabled.
- Actions: save draft, submit, reopen rejected draft, print/export own timesheet.

### Payroll admin
- Pay-run timesheet dashboard grouped by status: not started, draft, submitted, approved, rejected, locked/imported.
- Actions: open employee timesheet, make correction with reason, approve, reject with reason, bulk approve submitted timesheets, import approved hours into draft pay run, view audit history.

### Payroll integration
- MVP timesheets are keyed by explicit `period_start` and `period_end`; they are created before pay runs and linked to a pay run only when approved hours are imported or processed.
- Draft pay-run creation defaults hourly employee hours from approved timesheets for the selected period.
- Missing/unapproved hourly timesheets produce a blocking warning unless admin explicitly uses a controlled override.
- `PayStub` stores source timesheet linkage when generated from approved timesheets.
- Processing a pay run locks linked timesheets and prevents silent edits.
- Add a service seam such as `app/services/payroll_timesheet_integration.py` for approved-timesheet lookup, missing/unapproved readiness checks, import mapping, and lock-on-process logic; do not grow `app/routes/payroll.py::create_pay_run` or `process_pay_run` with this orchestration.

## Data model proposal
Prefer a new `app/models/timesheets.py` module to keep the lifecycle distinct from final payroll stubs.

### `EmployeePortalLink` or equivalent
- Store the employee-user link on the auth/master side, because `User`/`UserMembership` live in the master auth database while `Employee` lives in the selected company database.
- Fields: `id`, `user_id`, `company_scope`, `employee_id`, `is_active`, timestamps, optional `created_by_user_id` / `deactivated_by_user_id`.
- Do **not** rely on a normal database foreign key from this link to company-scoped `employees`; resolve `employee_id` by opening the authorised company database for `company_scope`.
- Unique constraints must prevent ambiguous active links, especially multiple active links for the same `(user_id, company_scope)` and duplicate active user links to the same employee.

### `Timesheet`
- `id`, `employee_id`, required `period_start` / `period_end`, nullable `pay_run_id` assigned only during import/process linkage.
- `status`, `total_hours`, submitted/approved/rejected/locked timestamps and actor IDs.
- `rejection_reason`, notes, timestamps.

### `TimesheetLine`
- `id`, `timesheet_id`, `work_date`, `entry_mode` (`duration` or `start_end`).
- `hours`, `start_time`, `end_time`, `break_minutes`.
- Optional `project_id`, `customer_id`, `task_code`, `description`, notes, timestamps.

### `TimesheetAuditEvent`
- `id`, `timesheet_id`, optional `timesheet_line_id`, `actor_user_id`.
- `event_type`, JSON old/new values or focused changed fields, reason/note, timestamp.

### Pay-stub linkage
- Add nullable `timesheet_id` to `PayStub` once the import slice is implemented.

## API proposal
### Employee self-service
- `GET /api/timesheets/self` — list own timesheets.
- `GET /api/timesheets/self/{timesheet_id}` — get own timesheet detail.
- `POST /api/timesheets/self` — create draft for own employee record and period.
- `PUT /api/timesheets/self/{timesheet_id}` — update own draft/rejected timesheet.
- `POST /api/timesheets/self/{timesheet_id}/submit` — submit own timesheet.
- `GET /api/timesheets/self/{timesheet_id}/export` — own CSV/print export.
- `GET /api/payroll/self/payslips` or equivalent employee-portal route — list only the linked employee's processed pay stubs.
- `GET /api/payroll/self/payslips/{run_id}/pdf` or equivalent employee-portal route — download only the linked employee's payslip PDF.

### Admin
- `GET /api/timesheets/periods` — period-based readiness dashboard before a pay run exists.
- `GET /api/timesheets/pay-runs/{pay_run_id}` — pay-run readiness dashboard once a pay run exists.
- `GET /api/timesheets/{timesheet_id}` — admin detail.
- `PUT /api/timesheets/{timesheet_id}` — admin correction before approval/lock.
- `POST /api/timesheets/{timesheet_id}/approve` — approve.
- `POST /api/timesheets/{timesheet_id}/reject` — reject with reason.
- `POST /api/timesheets/bulk-approve` — bulk approve safe submitted timesheets.
- `GET /api/timesheets/{timesheet_id}/audit` — audit events.
- `GET /api/timesheets/export` — admin CSV export with filters.

### Payroll integration
- Extend pay-run creation/update flow so approved timesheet totals can populate `PayStub.hours`.
- Add a preview endpoint or payload field that returns missing/unapproved timesheets before pay-run creation.

## Permissions
Add explicit permissions so employee self-service does not reuse broad payroll admin permissions:
- `timesheets.self.view`
- `timesheets.self.create`
- `timesheets.self.submit`
- `timesheets.manage`
- `timesheets.approve`
- `timesheets.export`
- `payroll.self.payslips.view`

Add an `employee` or `employee_self_service` role whose permissions are limited to self-service data only.

## Implementation slices
### Slice 0 — Planning artifacts
Create and maintain this PRD, the paired test spec, and the multi-session todo backlog.

### Slice 1 — Employee identity linkage and RBAC foundation
- Add auth/master-side employee-user link model/schema/service that stores `company_scope` and company-local `employee_id` without assuming a cross-database FK.
- Add employee self-service role/permissions, including own payslip view permission if payslip self routes are delivered in Slice 3.
- Add admin invite/link/unlink workflow, initially API-first.
- Enforce server-side ownership checks by resolving the current user to an active employee link for the requested company scope.

### Slice 2 — Timesheet core model/service
- Add timesheet, line, and audit models.
- Add lifecycle validation service.
- Add total-hour calculation for duration and start/end modes.
- Add locked/rejected/approved edit rules.

### Slice 3 — Employee self-service API
- Add timesheet `self` endpoints.
- Enforce current user to employee mapping.
- Add save draft, submit, list, detail, export basics.
- Add own-payslip list/PDF endpoints or a dedicated employee portal payroll route that never grants broad `payroll.payslips.view`.

### Slice 4 — Admin review API
- Add pay-period/pay-run readiness lists.
- Add approve/reject/correct/bulk approve/audit endpoints.
- Add CSV export.

### Slice 5 — Payroll integration
- Add `app/services/payroll_timesheet_integration.py` or equivalent service seam for readiness, import, and locking.
- Import approved timesheet totals into draft pay runs.
- Store source `timesheet_id` on stubs.
- Lock timesheets after payroll processing.
- Preserve manual hours path behind explicit override if needed.

### Slice 6 — Employee UI
- Add employee portal route/page.
- Add timesheet entry form with total-hours and start/end modes.
- Add submit/status/export affordances.

### Slice 7 — Admin UI
- Add timesheet review dashboard.
- Add approval/rejection/correction/audit views.
- Add payroll pay-run integration controls.

### Slice 8 — Project/client/task reporting
- Surface optional project/task metadata.
- Add summary reporting by employee/project/client/task.
- Add budget-readiness hooks without blocking payroll MVP.

### Slice 9 — Hardening and compliance pass
- Review retention, audit integrity, sensitive logging, and access boundaries.
- Add negative access tests and export tests.
- Verify no broad payroll data leaks to employee users.

## Impacted files and likely blast radius
- `app/models/payroll.py` — PayStub source linkage and employee relationships.
- New `app/models/timesheets.py` — primary data model.
- `app/models/auth.py` — master-side user/employee linkage and company-scope mapping.
- `app/models/__init__.py` — model imports.
- New `app/schemas/timesheets.py` — request/response contracts.
- `app/schemas/payroll.py` — pay-run source-timesheet fields if exposed.
- New `app/services/timesheets.py` — lifecycle, totals, ownership, audit.
- `app/services/auth.py` — permissions/roles and employee auth context helpers.
- New `app/services/employee_portal.py` or equivalent — active employee-link resolution across auth/master and company databases.
- New `app/routes/timesheets.py` — API routes.
- New `app/services/payroll_timesheet_integration.py` — approved hours import/readiness/locking seam.
- `app/routes/payroll.py` — thin integration calls only; avoid expanding large create/process route functions.
- `app/main.py` — router registration.
- `app/static/js/payroll.js` — admin integration.
- New or existing employee portal JS/CSS under `app/static/js/` and `app/static/css/`.
- Tests under `tests/`, especially auth, payroll, and JS route/render tests.

## Acceptance criteria
1. Employees can log in and only access their linked employee record, own timesheets, and own pay records/payslips for the active company scope.
2. Employees can create, edit, save, and submit timesheets for open pay periods.
3. Total hours are calculated correctly for total-hours and start/end/break entry modes.
4. Payroll admins can review, correct with an audit reason, approve, reject, bulk approve, and export timesheets.
5. Approved timesheets populate hourly pay-run stubs without manual re-entry.
6. Processed pay runs lock linked timesheets and preserve historical payroll source data.
7. Missing or unapproved timesheets are visible before payroll processing.
8. Timesheet records have auditable lifecycle events and are retained as wage/time records.
9. Light/dark UI remains usable and mobile-friendly enough for employee self-service.
10. Existing payroll calculations and payslip generation continue to pass.

## Security and privacy requirements
- Employee routes must never trust client-supplied `employee_id` without verifying linkage to authenticated user and active company scope.
- Admin routes must require explicit timesheet/payroll permissions.
- Timesheet exports must be scoped and filename-safe.
- Audit events must not expose secrets or raw session tokens.
- Sensitive employee/payroll fields must not appear in logs or frontend state beyond the authorised user.
- Pay-run locking must prevent tampering with historical wage/time records.
- Follow-up recommended before broad payroll portal rollout: continue addressing the repo's known broader auth/privacy hardening risks for employee/payroll data.

## Risks and mitigations
- **High — privacy leak between employees.** Mitigate with server-side ownership checks and negative tests for cross-employee access.
- **High — payroll record tampering.** Mitigate with locked states, audit events, and no silent edits after processing.
- **High — payroll calculation regressions.** Mitigate by keeping approved timesheets as input to existing `calculate_payroll_stub` rather than duplicating payroll math.
- **Medium — period/pay-run ambiguity.** Mitigated for MVP by requiring explicit period dates first and linking to pay runs only when approved time is imported/processed.
- **Medium — start/end edge cases.** Mitigate with clear validation for overnight shifts, breaks, decimal precision, and invalid ranges.
- **Medium — UI scope creep.** Mitigate by building the API/lifecycle first and deferring leave/expenses/native mobile/project analytics.

## Open decisions for future slices
- Confirmed for MVP: timesheets are period-keyed and created before pay runs; `pay_run_id` linkage is assigned only during import/process.
- Whether overnight shifts are allowed in MVP or deferred.
- Whether salary employees can submit exception timesheets initially.
- Whether project/client/task fields should reference existing customer/project tables or start as free-text metadata.
- Whether employee portal onboarding sends email invites now or uses admin-created credentials first.

# PRD — Payroll Slice 3: employee self-service timesheet and payslip API

## Date
2026-04-30

## Objective
Expose the first employee-facing payroll API surface by letting a linked employee manage only their own draft/submitted timesheets and view only their own processed payslips, using the Slice 1 employee portal link and Slice 2 timesheet service as the mandatory ownership boundary.

## Requirements summary
- Parent feature plan: `.omx/plans/prd-payroll-timesheets-2026-04-30.md`.
- Parent test spec: `.omx/plans/test-spec-payroll-timesheets-2026-04-30.md`.
- Parent todo: `.omx/plans/todo-payroll-timesheets-2026-04-30.md`.
- Slice 1 foundation already resolves the active user's company-local employee link via `resolve_employee_link` in `app/services/employee_portal.py:185-205` and exposes `/api/employee-portal/self` at `app/routes/employee_portal.py:46-52`.
- Slice 1 self-service permissions exist in `app/services/auth.py:47-52`, and the `employee_self_service` role deliberately contains only self permissions at `app/services/auth.py:128-137`.
- Slice 2 timesheet lifecycle functions already create/update/submit/approve/reject/lock records in `app/services/timesheets.py:170-335`; this slice must wrap only the employee-safe subset.
- Timesheet response schemas currently expose IDs, period/status/totals, lines, and audit events without employee payroll-private fields in `app/schemas/timesheets.py:56-109`.
- Existing admin payroll payslip PDF route requires broad `payroll.payslips.view` at `app/routes/payroll.py:303-329`; this slice must add own-payslip access guarded by `payroll.self.payslips.view` instead of weakening the admin route.
- Router registration lives in `app/main.py:24-42` and `app/main.py:121-125`; adding `app/routes/timesheets.py` requires an explicit import/include.
- Code-review graph context for the likely files reports high risk (1.00) with affected auth/bootstrap/login/create-user flows, so route changes must stay additive and permission-scoped.

## Constraints
- High-risk payroll/PII slice: write tests first, keep scope narrow, and perform an explicit security review before commit/push.
- Do not trust any client-supplied `employee_id` for self-service operations. Derive ownership only from `resolve_employee_link`.
- Do not introduce admin review, bulk approval, pay-run import, payroll locking, UI, project/client/task metadata, or email payslip delivery.
- Do not add dependencies; use stdlib `csv`/`io` for CSV export.
- Do not expand `employee_self_service` beyond `timesheets.self.*` and `payroll.self.payslips.view`.
- Keep existing admin payroll endpoints and permission semantics unchanged.
- A linked employee may create/update/submit only their own draft/rejected timesheets. They may not approve, reject, lock, or edit submitted/approved/locked timesheets.

## Implementation sketch
1. **Tests first**
   - Add `tests/test_timesheets_self_service_routes.py` covering own create/list/detail/update/submit/export, spoofed ownership, missing link, unauthenticated/wrong-permission cases, and locked-edit denial.
   - Extend or add payslip self-service tests in `tests/test_payroll_payslips.py` for own list/PDF access and cross-employee denial.
2. **Self-service schemas**
   - Extend `app/schemas/timesheets.py` with a self-service create request that omits `employee_id` (for example `TimesheetSelfCreateRequest`) and reuses `TimesheetUpdateRequest` / response schemas.
   - If payslip list needs a dedicated minimal schema, add it to `app/schemas/payroll.py` or a small new self-service schema; avoid exposing full `PayRunResponse` with other employees' stubs.
3. **Timesheet service read helpers**
   - Add employee-scoped helpers in `app/services/timesheets.py`:
     - list timesheets for one `employee_id` with optional date/status filters;
     - load a timesheet by `timesheet_id + employee_id` or raise 404;
     - produce CSV text for one owned timesheet.
   - Keep lifecycle mutation authorization in the route/service wrapper by checking ownership before calling `update_timesheet` or `submit_timesheet`.
4. **Employee self-service timesheet routes**
   - Add `app/routes/timesheets.py` with prefix `/api/timesheets`.
   - Proposed endpoints:
     - `GET /api/timesheets/self` — list only the linked employee's timesheets.
     - `POST /api/timesheets/self` — create draft for linked employee using `timesheets.self.create`.
     - `GET /api/timesheets/self/{timesheet_id}` — detail only if owned.
     - `PUT /api/timesheets/self/{timesheet_id}` — update only owned draft/rejected.
     - `POST /api/timesheets/self/{timesheet_id}/submit` — submit only owned draft/rejected.
     - `GET /api/timesheets/self/{timesheet_id}/csv` — export only owned timesheet with safe filename/header.
   - Every endpoint resolves ownership via `resolve_employee_link(master_db, db, auth)` and never accepts an `employee_id` path/query/body override.
5. **Own-payslip routes**
   - Add own-payslip endpoints under `app/routes/payroll.py` or a thin payroll self-service helper, guarded by `require_permissions("payroll.self.payslips.view")`:
     - `GET /api/payroll/self/payslips` — list processed pay-run stubs for the linked employee only, returning minimal run/stub summary.
     - `GET /api/payroll/self/payslips/{run_id}/pdf` — render only the linked employee's processed-run payslip.
   - Reuse `generate_payroll_payslip_pdf` from `app/routes/payroll.py:17` / `app/services/pdf_service.py` and the same processed-run check used by the admin PDF route at `app/routes/payroll.py:310-324`.
6. **Router registration**
   - Import/include `timesheets.router` in `app/main.py` alongside existing Phase 6 routes.
7. **Security review**
   - Document explicit IDOR, permission, export-header, and payroll-PII findings in `docs/security-review-payroll-employee-self-service-api-2026-04-30.md`.

## Impacted files and blast radius
- New `app/routes/timesheets.py` — employee-owned timesheet list/detail/create/update/submit/export routes.
- `app/main.py` — route import/include only.
- `app/services/timesheets.py` — employee-scoped query/export helpers; lifecycle behavior should remain unchanged.
- `app/schemas/timesheets.py` — self-create request and any route-specific response refinements.
- `app/routes/payroll.py` — own-payslip list/PDF endpoints or a small import if split into a helper.
- `app/schemas/payroll.py` — minimal own-payslip list response if needed.
- New/updated tests: `tests/test_timesheets_self_service_routes.py`, `tests/test_payroll_payslips.py`, and targeted auth/portal regressions.
- No expected changes to models or Alembic migrations in this slice.

## Acceptance criteria
1. A linked `employee_self_service` user can create a draft timesheet for their active employee link without providing `employee_id`.
2. Self list/detail endpoints return only timesheets whose `employee_id` matches the active employee link.
3. Self create/update/submit endpoints ignore or reject spoofed `employee_id` attempts and never mutate another employee's timesheet.
4. Missing, inactive, or wrong-scope employee links cause self routes to fail without exposing whether other employees/timesheets exist.
5. Submitted/approved/locked timesheets cannot be edited through self routes.
6. Self-service users cannot approve, reject, lock, or access admin payroll/timesheet actions.
7. Own timesheet CSV export includes only the owned timesheet's period/line/status/hour fields and uses a deterministic safe filename.
8. A linked employee can list and download only their own processed-run payslip PDFs via `payroll.self.payslips.view`.
9. A linked employee cannot download another employee's payslip by changing `run_id`, `employee_id`, path, or query values.
10. Existing admin payroll payslip tests and employee portal link tests continue to pass.

## Verification steps
- `python -m pytest tests/test_timesheets_self_service_routes.py`
- `python -m pytest tests/test_payroll_payslips.py`
- `python -m pytest tests/test_employee_portal_auth.py tests/test_timesheets_service.py`
- `python -m pytest tests/test_auth_rbac.py tests/test_auth_company_access_controls.py`
- `python -m compileall app/routes app/services app/schemas tests`
- `git diff --check`
- Manual smoke (route-function or TestClient if practical): bootstrap owner, create employee/self-service user, link employee, log in as employee, create/update/submit own timesheet, export CSV, process pay run, download own payslip, confirm cross-employee attempts return 404/403.

## Security review checklist
- Auth/permission boundary: every self route uses `timesheets.self.*` or `payroll.self.payslips.view`; no broad payroll/admin permission is granted to employee role.
- Ownership boundary: every self route derives `employee_id` from `resolve_employee_link`; client ownership inputs are absent or ignored/rejected.
- IDOR: route tests cover another employee's timesheet/payslip IDs and wrong company scope.
- PII: list/detail/export responses omit IRD number, pay rate, tax code, deduction settings, and other employees' pay-run data.
- Export safety: CSV headers are fixed, filenames contain only generated IDs/dates, and response headers do not include user-provided names.
- Shell/filesystem/SSRF/deserialization: no new shell execution, filesystem write, outbound request, upload parsing, or unsafe deserialization.
- Dependency risk: no new dependencies.

## Risk notes
- **High — IDOR across employee payroll records:** mitigated by ownership resolution from Slice 1 and negative tests for spoofed IDs.
- **High — payslip PII exposure:** mitigate with own-only queries and minimal list response rather than reusing full admin pay-run responses.
- **Medium — route/service lifecycle mismatch:** route wrappers must scope by employee before calling ID-only service mutations.
- **Medium — CSV formula/header concerns:** export only fixed headers and server-controlled values; do not include user-provided filename fragments.
- **Medium — route registration blast radius:** keep `app/main.py` change import/include-only and run import/compile checks.

## Out of scope
- Admin review API, bulk approval, correction/rejection UI, pay-run import from timesheets, timesheet locking through payroll processing, employee frontend pages, project/client/task metadata, email payslip self-send, and final compliance hardening.

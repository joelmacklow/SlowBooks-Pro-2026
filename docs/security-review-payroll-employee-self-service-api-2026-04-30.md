# Security review: payroll employee self-service API (Slice 3)

## Date
2026-04-30

## Scope reviewed
- `app/routes/timesheets.py`
- `app/services/timesheets.py`
- `app/routes/payroll.py` (new `/api/payroll/self/payslips*` endpoints)
- `app/schemas/timesheets.py`
- `app/schemas/payroll.py`
- `app/main.py`
- `tests/test_timesheets_self_service_routes.py`
- `tests/test_payroll_payslips.py`

## Threat-focused checks
1. **Auth/permission boundary**
   - Verified self-service timesheet routes require only `timesheets.self.*`.
   - Verified own-payslip routes require `payroll.self.payslips.view`.
   - Verified admin payslip route still requires `payroll.payslips.view`.

2. **Ownership/IDOR boundary**
   - Verified all self routes derive employee ownership via `resolve_employee_link(master_db, db, auth)`.
   - Verified no self route accepts authoritative `employee_id` input for ownership decisions.
   - Verified cross-employee timesheet detail/update/export and payslip download attempts return denied responses.

3. **PII minimization**
   - Timesheet self list/detail/export responses do not expose employee payroll-private fields (`ird_number`, tax settings, pay rate, etc.).
   - Own-payslip list uses a minimal summary response and does not expose other employees’ stubs.

4. **CSV/export safety**
   - Timesheet CSV export uses fixed headers and server-generated filename.
   - No user-supplied filename fragments are used in response headers.
   - Export payload omits free-text notes and payroll-private fields, reducing formula/content injection risk.

5. **High-risk primitives**
   - No new shell execution, outbound HTTP, upload parsing, filesystem writes, or unsafe deserialization introduced.
   - No new dependency introduced.

## Findings
- **No CRITICAL/HIGH issues identified in this slice.**
- Residual risk remains **MEDIUM (product-level)** because broader app auth/trust assumptions and multi-company hardening are follow-up work outside this slice.

## Verification evidence
- `python -m unittest tests.test_timesheets_self_service_routes`
- `python -m unittest tests.test_payroll_payslips`
- `python -m unittest tests.test_employee_portal_auth tests.test_timesheets_service tests.test_auth_rbac tests.test_auth_company_access_controls`
- `python -m compileall app/routes app/services app/schemas tests`
- `git diff --check`

## UI bugfix addendum (admin link UI + self-service navigation)

### Additional scope reviewed
- `app/static/js/auth.js`
- `app/static/js/app.js`
- `app/static/js/timesheets_self_service.js`
- `index.html`
- `tests/js_auth_page.test.js`
- `tests/js_auth_company_scopes.test.js`

### Additional checks
1. **Permission-gated navigation**
   - Added `My Timesheets` and `My Payslips` routes are permission-gated by existing self-service permissions in `App.routes`.
   - Sidebar visibility still flows through route permission checks in `syncNavVisibility`.
2. **Admin linking workflow**
   - UI uses existing `/api/employee-portal/links` APIs; no permission broadening or direct DB mutation path added.
   - Deactivation path uses existing guarded endpoint and explicit operator confirmation.
3. **Data exposure**
   - Employee-link UI renders minimal user/employee summary values only.
   - No new private payroll fields introduced in frontend payloads or displays.

### Additional verification evidence
- `node --check app/static/js/auth.js`
- `node --check app/static/js/app.js`
- `node --check app/static/js/timesheets_self_service.js`
- `for f in tests/js_*.test.js; do node "$f"; done`

### Addendum finding
- **No CRITICAL/HIGH issues identified in this UI bugfix addendum.**

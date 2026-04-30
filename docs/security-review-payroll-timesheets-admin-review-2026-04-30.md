# Security review: payroll timesheets admin review API (Slice 4)

## Date
2026-04-30

## Scope reviewed
- `app/services/auth.py`
- `app/schemas/timesheets.py`
- `app/services/timesheets.py`
- `app/routes/timesheets.py`
- `tests/test_timesheets_admin_routes.py`
- `tests/test_admin_rbac_protection.py` (permission boundary context)

## Threat-focused checks
1. **Auth/permission boundary**
   - Admin review routes require explicit timesheet permissions:
     - `timesheets.manage` for readiness, detail, correction, and audit
     - `timesheets.approve` for approve/reject/bulk-approve
     - `timesheets.export` for CSV export
   - `payroll_admin` now receives those permissions explicitly; `payroll_viewer` does not.
   - Employee self-service permissions were not broadened.

2. **Ownership and data-access boundary**
   - Admin routes are intentionally company-scoped, not employee-scoped, and do not accept user ownership as a control.
   - Self-service ownership checks remain unchanged in the `/self/*` routes.
   - No IDOR-sensitive route was added that would allow bypassing the timesheet permission gate.

3. **Mutation safety**
   - Submitted-timesheet correction keeps status submitted and records a dedicated audit event with a required reason.
   - Approve/reject/bulk-approve all enforce current status before mutating.
   - Bulk approve validates all requested IDs before applying updates, reducing partial-approval risk.

4. **CSV/export safety**
   - Admin CSV export uses a server-generated filename derived from fixed period/status values.
   - The export payload omits free-text notes and payroll-private employee fields such as ird/tax configuration and pay rate.
   - Status is validated before being reused in the filename, so untrusted input does not flow directly into headers.

5. **Sensitive logging / primitives**
   - No new shell execution, file writes, outbound requests, or unsafe deserialization were introduced.
   - No new dependency was added.

## Findings
- **No CRITICAL/HIGH issues identified in this slice.**
- Residual risk remains **MEDIUM** because the application still relies on the broader authenticated-local/private deployment model for payroll data, and future RBAC/privacy hardening may still be warranted.

## Verification evidence
- `python -m unittest tests.test_timesheets_admin_routes`
- `python -m unittest tests.test_timesheets_self_service_routes tests.test_employee_portal_auth tests.test_admin_rbac_protection tests.test_timesheets_admin_routes`
- `python -m py_compile app/services/auth.py app/schemas/timesheets.py app/services/timesheets.py app/routes/timesheets.py tests/test_timesheets_admin_routes.py`
- `git diff --check`


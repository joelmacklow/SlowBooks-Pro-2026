# Security Review — RBAC Rollout + Auth UX (2026-04-14)

## Scope Reviewed
- `app/services/auth.py`
- `app/routes/auth.py`
- `app/routes/settings.py`
- `app/routes/accounts.py`
- `app/routes/backups.py`
- `app/routes/audit.py`
- `app/routes/companies.py`
- `app/static/js/auth.js`
- `app/static/js/app.js`
- `app/static/js/api.js`

## Review Focus
- Login/session UX and session handling
- Whether newly protected admin routes now fail closed without the right permissions
- Whether the role-template-plus-override model remains granular enough for future separation of duties

## Findings
1. **Sensitive admin surfaces now share the same RBAC enforcement model as payroll**
   - Settings, accounts/system-account roles, backups, audit, and companies now require explicit permissions.
   - This reduces the prior gap where payroll was protected but adjacent admin surfaces remained wide open.

2. **Auth UX reduces reliance on API-only bootstrap/admin operations**
   - Login, bootstrap-admin, logout, and user-management UX now exist in the app shell.
   - This lowers operational friction and makes it more realistic that admins will actually use the RBAC system rather than bypass it.

3. **Granular overrides remain the main defense against over-broad canned roles**
   - Role templates are still only starting points; allow/deny overrides continue to be available per membership.
   - This is positive for bookkeeping/payroll separation-of-duties, which the user explicitly requested.

## Residual Risks
- Most day-to-day business modules (customers, invoices, payments, banking, reports, imports/exports) are not yet rolled onto RBAC enforcement.
- There is still no cross-company auth context switching UX; the current database remains the effective company scope for this rollout.
- Bearer tokens are stored in browser localStorage, which is acceptable for the current trusted deployment model but should be revisited if the product moves toward less-trusted hosting environments.

## Conclusion
- No new CRITICAL/HIGH issues identified in this slice.
- Residual risk is **MEDIUM** because RBAC is now credible for payroll/admin data, but broader module coverage and future deployment hardening still remain.

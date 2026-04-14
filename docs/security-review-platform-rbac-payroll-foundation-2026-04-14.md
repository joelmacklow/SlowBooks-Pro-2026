# Security Review — Platform RBAC Foundation with Payroll Privacy (2026-04-14)

## Scope Reviewed
- `app/models/auth.py`
- `app/services/auth.py`
- `app/routes/auth.py`
- `app/routes/employees.py`
- `app/routes/payroll.py`
- `app/static/js/api.js`
- `alembic/versions/f6a7b8c9d0e1_add_platform_auth_rbac_foundation.py`

## Review Focus
- Authentication/session handling for the new payroll-protection boundary
- Role and permission resolution, including per-membership overrides
- Whether employee and payroll endpoints now fail closed without a valid session/permission

## Findings
1. **Payroll/employee endpoints now default-deny instead of being anonymously accessible**
   - The new auth/RBAC layer protects employee CRUD, payroll runs, payslips, and filing/export routes.
   - This materially reduces the previously documented exposure of payroll PII.

2. **Granular permission overrides reduce pressure to over-grant broad roles**
   - Role templates are now composable with explicit allow/deny overrides per membership.
   - This is a safer foundation than a small set of rigid coarse roles because sensitive payroll actions can be granted narrowly.

3. **Session handling is token-based and hashed at rest**
   - Raw bearer tokens are not stored directly in the database; only SHA-256 token hashes are persisted.
   - Passwords are stored using PBKDF2-HMAC-SHA256 with per-password random salts.

## Residual Risks
- The broader app surface is not yet fully protected by the new RBAC model; only payroll/employee routes are enforced in this slice.
- There is not yet a first-class UI for login/user management, so bootstrap and initial admin/user provisioning are API-driven.
- CORS and broader app trust-boundary hardening outside the protected payroll domain remain follow-up work.

## Conclusion
- No new CRITICAL/HIGH issues identified in this slice.
- Residual risk drops for payroll PII specifically, but broader platform auth rollout still remains **MEDIUM** until more domains adopt the new foundation.

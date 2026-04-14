# Platform RBAC Foundation with Payroll Privacy Specification

## Goal
Create a reusable authentication and RBAC foundation for the platform, and use payroll/employee data as the first enforced protected domain.

## Required Behavior
- Add user, membership/role assignment, permission override, and auth-session persistence.
- Add auth routes for first-admin bootstrap, login, logout, current-session inspection, and admin-managed user creation/update.
- Resolve permissions from role templates plus explicit allow/deny overrides.
- Require auth + permissions for employee CRUD, employee filing export, payroll run read/create/process, payslip PDF/email, and Employment Information export.
- Keep the current database as the initial company scope for membership resolution.
- Deny protected requests by default when no valid session or permission is present.

## Constraints
- No new third-party dependencies.
- Reuse the existing FastAPI/SQLAlchemy stack and add an Alembic migration for new auth tables.
- Preserve existing non-payroll route behavior in this slice.
- The slice must be usable without a full product-wide RBAC rollout.

## Verification
- Backend tests for bootstrap, login, permission resolution, override behavior, and payroll/employee route enforcement.
- Full Python and JS suites, Python syntax compilation, touched-JS syntax checks if needed, and `git diff --check`.

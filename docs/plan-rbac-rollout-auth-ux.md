# RBAC Rollout + Auth UX Slice

## Summary
Build first-class login/session/user-management UX on top of the new RBAC foundation and extend the same permission model to the next sensitive/admin modules.

## Key Changes
- Add frontend login/bootstrap/logout/session UX.
- Add a user-management UI for role templates and permission overrides.
- Extend RBAC enforcement to settings, chart of accounts/system-account roles, backups, audit log, and companies.
- Update app shell/nav behavior so protected areas route through auth UX instead of only surfacing backend failures.
- Add auth/RBAC rollout docs and tests.

## Test Plan
- Add failing backend tests for newly protected admin routes.
- Add failing frontend tests for login/bootstrap/logout/user-management rendering and bearer-token behavior.
- Re-run full Python/JS verification, syntax checks, and `git diff --check`.

## Defaults
- Use the existing RBAC foundation and current DB/company scope.
- Keep role templates customizable through permission overrides.
- Focus this slice on auth UX and sensitive/admin module rollout, not full product-wide enforcement.

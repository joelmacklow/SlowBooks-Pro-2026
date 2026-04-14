# RBAC Rollout + Auth UX Specification

## Goal
Make the RBAC foundation usable in the product and extend it beyond payroll by adding auth/session UX plus protection for the main sensitive/admin surfaces.

## Required Behavior
- Add a login/bootstrap UX for unauthenticated users.
- Add a user-management UX for listing users, creating users, updating role templates, and editing allow/deny permission overrides.
- Add explicit permissions and backend enforcement for settings, accounts/system-account roles, backups, audit log, and companies.
- Route unauthenticated users to login/bootstrapping for protected pages instead of only showing backend error responses.
- Show current authenticated user/session state in the app shell and support logout.

## Constraints
- No new third-party dependencies.
- Reuse the existing auth/session/token model and capability-based permission overrides.
- Keep broader low-risk module rollout out of scope for this slice.
- Preserve NZ-first behavior; auth rollout must not regress localized accounting/payroll flows.

## Verification
- Backend tests for newly protected admin routes and role enforcement.
- Frontend tests for login/bootstrap/user-management/logout rendering and auth header/session behavior.
- Full Python and JS suites, Python syntax compilation, touched-JS syntax checks, and `git diff --check`.

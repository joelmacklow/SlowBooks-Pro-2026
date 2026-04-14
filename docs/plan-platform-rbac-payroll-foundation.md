# Platform RBAC Foundation with Payroll Privacy Slice

## Summary
Establish the first reusable auth/RBAC foundation for SlowBooks NZ and enforce it on the payroll/employee domain first, where payroll PII now exists.

## Key Changes
- Add platform auth models and routes for users, memberships/role assignments, session login, and first-admin bootstrap.
- Define capability-based payroll/employee permissions and role templates with override support so later roles are not limited to coarse fixed bundles.
- Protect employee and payroll routes with explicit permission checks.
- Add payroll-focused auth/RBAC tests and a security review for the slice.
- Update summary/docs so the master todo reflects that payroll privacy now sits on a reusable RBAC foundation.

## Test Plan
- Add failing auth/RBAC tests first for bootstrap, login, permission resolution, and payroll/employee route protection.
- Re-run full Python/JS verification, syntax checks, and `git diff --check`.

## Defaults
- Current database scope acts as the initial company scope for this foundation.
- Payroll and employee endpoints become protected immediately; broader module rollout can follow in later slices.
- Use role templates plus per-membership allow/deny overrides rather than rigid hardcoded role limits.

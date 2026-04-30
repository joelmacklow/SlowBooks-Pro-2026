# Test Spec — Per-user company access controls

## Date
2026-04-17

## Red/Green plan
- Add backend tests proving:
  - user create/update can assign multiple company scopes
  - auth context resolves permissions for a requested company scope
  - unauthorized company scope access is denied
- Add frontend tests proving:
  - Users & Access modal renders company-scope controls
  - payload submission includes selected company scopes
- Re-run targeted company/auth shell tests to ensure no regressions.

## Verification
- New targeted auth/company backend tests
- Updated auth UI JS tests
- Existing company switching/nav tests
- `git diff --check`

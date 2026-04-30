# Test Spec — Companies status-bar database update bugfix

## Date
2026-04-17

## Red/Green plan
- Add a JS test for App.loadCompanyName/status-company rendering with selected company context.
- Confirm the current behavior fails when company_name is blank/default or when the selected database changes.
- Apply the smallest display logic fix.
- Re-run targeted companies/app-shell tests.

## Verification
- Targeted company/app JS tests
- `git diff --check`

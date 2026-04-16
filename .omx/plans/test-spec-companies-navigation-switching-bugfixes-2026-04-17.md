# Test Spec — Companies dashboard navigation and switching bugfixes

## Date
2026-04-17

## Red/Green plan
- Add a JS test covering app/nav route behavior for the Companies page.
- Add a JS test covering company switching persistence and API auth/request headers.
- Confirm the tests fail first.
- Implement the smallest shell/API/CompaniesPage fixes needed.
- Re-run targeted Companies/app-shell tests and safety checks.

## Verification
- Targeted Companies/app JS tests
- `git diff --check`

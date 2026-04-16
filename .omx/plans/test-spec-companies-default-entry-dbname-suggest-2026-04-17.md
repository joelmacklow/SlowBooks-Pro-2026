# Test Spec — Companies page default entry and database-name suggestion

## Date
2026-04-17

## Red/Green plan
- Add/update a JS test proving the Companies page includes the default company entry.
- Add a JS test proving the create modal auto-suggests a database name from company name input.
- Add/update a Python test for the companies API/service if needed to ensure the default company is included in the returned list.
- Confirm the tests fail first, then implement the smallest backend/UI change set.

## Verification
- Targeted Companies JS tests
- Any targeted Companies Python tests added/updated
- `git diff --check`

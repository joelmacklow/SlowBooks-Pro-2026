# Exception Exposure Hardening Slice

## Summary
Fix the CodeQL information-exposure findings in `app/routes/companies.py` and `app/routes/csv.py` by preventing internal exception details from leaking through HTTP errors.

## Key Changes
- Add regression tests first for company creation and CSV import failures carrying sensitive exception text.
- Return safe client-facing error messages for unexpected backend failures while preserving useful validation errors.
- Catch CSV decode/import exceptions at the route boundary and replace them with controlled HTTP error details.
- Keep normal success paths and expected user-correctable validation responses unchanged.

## Test Plan
- Add failing route-level tests that simulate sensitive exception messages and assert they are not exposed.
- Re-run targeted tests, full Python suite, JS tests, syntax checks, and `git diff --check`.

## Defaults
- Unexpected internal failures should produce generic client-facing error messages.
- Safe validation/business-rule messages may still be surfaced when they are intentionally user-facing.
- No new dependencies.

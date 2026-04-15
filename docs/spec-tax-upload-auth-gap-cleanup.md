# Tax And Upload Auth Gap Cleanup Specification

## Goal
Eliminate the remaining public tax/upload exceptions left after the RBAC rollout by making the legacy tax API explicitly retired for SlowBooks NZ and making logo uploads require existing settings privileges.

## Required Behavior
- `/api/tax/schedule-c`, `/api/tax/schedule-c/csv`, and `/api/tax/mappings` list/create must all return the NZ retired-tax response and must not behave as active product APIs.
- `/api/uploads/logo` must require authenticated users with `settings.manage`.
- Successful authorized logo uploads must continue validating image MIME types, saving the file, and updating `company_logo_path` as today.
- No new tax UI or permission keys should be introduced.

## Constraints
- Keep the change localized to tax/upload routes and focused tests/docs.
- No schema migrations or storage redesign.
- Preserve existing NZ disabled-tax messaging so users are steered toward GST workflows.

## Verification
- Backend tests for retired tax mappings and protected logo upload access.
- Full Python and JS suites, syntax checks, and `git diff --check`.

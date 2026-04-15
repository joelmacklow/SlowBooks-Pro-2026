# Tax And Upload Auth Gap Cleanup Slice

## Summary
Close the remaining public tax/upload gaps after the broader RBAC rollout by retiring the dormant legacy NZ tax API surface and protecting company-logo uploads behind existing settings permissions.

## Key Changes
- Disable the legacy `/api/tax/mappings` endpoints with the same NZ-facing retired-tax response used for Schedule C.
- Leave the legacy tax page/nav absent; do not reintroduce any active NZ income-tax UI in this slice.
- Require `settings.manage` on `/api/uploads/logo` while keeping current image validation and stored setting behavior.
- Add regression tests for disabled tax mappings and protected logo upload access.

## Test Plan
- Extend Schedule C-disabled coverage to the tax mappings endpoints.
- Add upload auth tests for unauthenticated, unauthorized, and authorized logo uploads.
- Re-run full Python/JS verification, syntax checks, and `git diff --check`.

## Defaults
- Fully retire dormant tax mappings now rather than keeping a protected compatibility API.
- Reuse existing `settings.manage` instead of adding a new uploads-specific permission.
- No schema migrations or new frontend routes.

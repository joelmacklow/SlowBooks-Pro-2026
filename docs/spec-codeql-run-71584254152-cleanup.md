# Spec: resolve CodeQL run 71584254152 on nz-localization

## Goal
Close or supersede the linked CodeQL run by proving the reported backup-path, company-SQL, and exception-exposure findings are fixed on the current branch, or patch any residual gap if one remains.

## Required Behavior
- Backup routes and services must reject invalid backup filenames before filesystem or subprocess access.
- Company database names must be validated before administrative SQL or derived database URLs are constructed.
- Company creation and CSV import routes must not expose internal exception details to API clients.
- If the linked run is stale relative to current branch state, the review artifact must say so explicitly with the current hardening evidence.

## Verification
- `tests.test_backup_path_hardening`
- `tests.test_company_service_sql_hardening`
- `tests.test_exception_exposure_hardening`
- full Python unittest discover suite
- syntax/compile check for touched security files
- `git diff --check`

## Assumptions
- The linked run predates current hardening commits unless verification proves otherwise.
- This slice should stay security-only and avoid mixing with unrelated in-progress work.

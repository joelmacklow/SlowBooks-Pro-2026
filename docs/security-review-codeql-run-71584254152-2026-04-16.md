# Security Review — CodeQL Run 71584254152 (2026-04-16)

## Scope Reviewed
- `app/routes/backups.py`
- `app/services/backup_service.py`
- `app/services/company_service.py`
- `app/routes/companies.py`
- `app/routes/csv.py`
- `tests/test_backup_path_hardening.py`
- `tests/test_company_service_sql_hardening.py`
- `tests/test_exception_exposure_hardening.py`

## Linked Run
- GitHub Actions / CodeQL run: `71584254152`
- Requested scope: the linked run only, not a broader repo-wide security sweep

## Review Focus
- Backup-path traversal / uncontrolled filename handling
- Company database-name validation before administrative SQL and derived DB URLs
- Exception/message exposure from company creation and CSV import routes

## Findings
1. **Backup path handling is already hardened on the current branch**
   - Download, restore, and backup-list visibility all route through the shared `resolve_backup_path()` validator.
   - The helper rejects absolute paths, path separators, whitespace-mutated names, and filenames outside the managed `backups/` directory before any filesystem or `pg_restore` access.
   - This matches the hardening introduced in commit `7b70709`.

2. **Company database-name SQL handling is already hardened on the current branch**
   - Company database names are validated centrally via `_validate_database_name()` before URL generation, create/drop DDL, or bootstrap paths.
   - PostgreSQL DDL still uses dynamic identifiers, but only after validation plus quoting.
   - This matches the hardening introduced in commit `94238a6`.

3. **Company and CSV routes already hide internal exception details**
   - `/api/companies` returns controlled `public_error` text instead of raw backend exception messages.
   - CSV import routes convert decode failures to a safe 400 and unexpected importer failures to a generic 500.
   - This matches the hardening introduced in commit `b22f3db`.

4. **Conclusion: the linked CodeQL run is stale relative to current `nz-localization` state**
   - The alert families reported by the linked run correspond to security fixes that are already present in the current branch contents.
   - No additional application-code change was required to satisfy the linked run's findings during this slice.

## Verification Performed
- `.venv/bin/python -m unittest tests.test_backup_path_hardening tests.test_company_service_sql_hardening tests.test_exception_exposure_hardening`
- `.venv/bin/python -m unittest discover -s tests`
- `for f in tests/js_*.test.js; do node "$f"; done`
- `.venv/bin/python -m py_compile app/routes/backups.py app/services/backup_service.py app/services/company_service.py app/routes/companies.py app/routes/csv.py tests/test_backup_path_hardening.py tests/test_company_service_sql_hardening.py tests/test_exception_exposure_hardening.py`
- `git diff --check`

## Residual Risks
- The linked GitHub run itself will remain open/stale until a newer CodeQL analysis runs against the current branch/PR state.
- The test suite still emits pre-existing `ResourceWarning` noise for unclosed SQLite connections; these warnings did not indicate a failure in the reviewed security controls.
- This review intentionally did not extend to unrelated current branch security topics outside the linked run.

## Recommended Next Step
- Trigger or wait for a fresh CodeQL run against the current `nz-localization` branch/PR so the stale alert set is superseded by analysis of the hardened code.

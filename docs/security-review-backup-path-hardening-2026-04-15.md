# Security Review — Backup Path Hardening (2026-04-15)

## Scope Reviewed
- `app/services/backup_service.py`
- `app/routes/backups.py`
- `tests/test_backup_path_hardening.py`

## Review Focus
- Whether backup download and restore now reject traversal-style path input before filesystem access
- Whether the fix keeps backup operations constrained to app-managed files inside `BACKUP_DIR`
- Whether the change introduces new authorization, subprocess, or file-handling regressions

## Findings
1. **Traversal-style backup filenames are now rejected at a shared trust boundary**
   - `resolve_backup_path()` treats backup filenames as untrusted input and rejects empty values, absolute paths, separators, and names outside the app-managed backup pattern.
   - Route download and service restore now both use that helper, eliminating the previously uncontrolled path joins.

2. **Backup listing no longer trusts stored filenames blindly**
   - The list route now skips database records whose filenames do not resolve to a valid managed backup path.
   - This avoids reintroducing path traversal through stale or maliciously altered backup metadata.

3. **Restore no longer reaches `pg_restore` for invalid filenames**
   - Invalid backup names fail before subprocess invocation, reducing the risk of using attacker-controlled paths with restore tooling.
   - Regression coverage asserts that traversal input does not call `subprocess.run`.

## Residual Risks
- A valid backup filename still points to a file whose contents are fully trusted by `pg_restore`; backup authenticity/integrity verification is still out of scope for this slice.
- Backup creation/restoration remains an admin capability, so broader security still depends on the RBAC/session protections already in place.

## Conclusion
- No new CRITICAL/HIGH issues identified in this slice.
- Residual risk is **LOW to MEDIUM**, centered on the existing trust model for valid backup artifacts rather than uncontrolled path traversal.

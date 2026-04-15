# Backup Path Hardening Specification

## Goal
Ensure backup download and restore endpoints can only operate on validated backup files located inside the app-controlled backup directory.

## Required Behavior
- User-supplied backup filenames must be treated as untrusted input.
- Path traversal, absolute paths, path separators, and empty/whitespace-only filenames must be rejected.
- Valid backup operations must resolve only to files within `BACKUP_DIR`.
- Existing successful behavior for valid managed backup files must remain intact.

## Constraints
- Keep the current backup directory and backup creation flow.
- No new dependencies.
- Keep route/service changes small and reviewable.
- Prefer one shared validation helper over duplicated route-level ad hoc checks.

## Verification
- Backend tests proving invalid filenames are rejected and valid backup files still resolve.
- Targeted backup-path tests, full Python test suite, syntax checks, and `git diff --check`.

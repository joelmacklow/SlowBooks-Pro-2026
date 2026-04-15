# Backup Path Hardening Slice

## Summary
Address the CodeQL uncontrolled-path findings in the backup download and restore flow by constraining all user-supplied backup filenames to validated files inside the managed backup directory.

## Key Changes
- Add regression tests first for traversal-style backup filenames on both the route and service layers.
- Centralize backup filename/path validation in the backup service so routes and restore logic share the same trust boundary.
- Reject invalid backup names before any filesystem access or subprocess invocation.
- Keep normal backup listing, download, and restore behavior unchanged for valid managed backup files.

## Test Plan
- Add failing backend tests covering traversal attempts, invalid filenames, and valid backup resolution.
- Re-run targeted tests, then full Python suite, JS checks as needed, syntax checks, and `git diff --check`.

## Defaults
- Only files directly inside the configured backup directory are valid backup targets.
- Do not broaden accepted filename patterns beyond the app-managed backup files in this slice.
- No new dependencies or storage redesign.

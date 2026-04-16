# Plan: resolve CodeQL run 71584254152 on nz-localization

## Summary
Validate the linked CodeQL run against the current `nz-localization` branch, preserve the existing hardening for backup paths, company database-name handling, and exception exposure, and only change application code if the linked alerts still reproduce on current branch state.

## Key Changes
- Reconfirm backup download/restore flows stay inside managed storage through shared filename validation.
- Reconfirm company database-name input is validated before any URL generation or PostgreSQL DDL.
- Reconfirm company creation and CSV import routes return controlled public errors instead of raw backend exception text.
- Record the review outcome in a dedicated security-review artifact so the stale run can be closed with evidence.

## Verification
- Run targeted security regression tests for backup paths, company DB-name validation, and exception exposure.
- Re-run the Python suite, syntax checks, and `git diff --check`.
- Compare the linked run's alert families with the current branch contents/commits to determine whether the run is stale or still actionable.

## Constraints
- Keep this slice isolated from the unrelated forum-carryover changes already in the working tree.
- Do not broaden into a repo-wide security sweep.
- No new dependencies.

# Test Spec — Repo cleanup for code-review-graph/tool excludes

## Date
2026-04-21

## Verification
- Confirm root `.gitignore` contains explicit entries for:
  - `.venv/`
  - `.pytest_cache/`
  - `.code-review-graph/`
  - `.nfs*`
- Run `git diff --check`.
- Optionally use `git check-ignore -v` on representative paths to confirm the new rules match.

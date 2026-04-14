# Master Todo Refresh Specification

## Goal
Make the master todo in `docs/localization_summary.md` accurately represent the current remaining NZ-localization work after the completed plan/spec slices already shipped.

## Required Behavior
- The master todo should stop listing already completed slices as pending work.
- The refreshed section should retain high-value ongoing guardrails (for example branch hygiene and NZ-first conventions) only where they still guide future implementation.
- Remaining items should be limited to unresolved follow-up work that is still explicitly deferred in the tracked plans/specs.

## Constraints
- This is a documentation-only slice.
- Do not rewrite historical plan/spec files; only refresh the summary todo.
- Prefer a concise remaining-work list over exhaustive historical restatement.

## Verification
- Manual cross-check against existing `plan-*` and `spec-*` docs.
- `git diff --check`.

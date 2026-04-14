# Master Todo Refresh Slice

## Summary
Reconcile the master todo in `docs/localization_summary.md` against the completed plan/spec artifacts so it reflects only the remaining NZ-localization work and ongoing guardrails.

## Key Changes
- Review completed `docs/plan-*.md` and `docs/spec-*.md` artifacts.
- Remove or collapse completed items from the master todo.
- Reframe the master todo around the substantive remaining slices and evergreen repo guardrails.
- Keep the todo grounded in tracked plan/spec outcomes rather than stale historical checkpoints.

## Test Plan
- Verify the refreshed todo matches completed plan/spec history.
- Run `git diff --check`.

## Defaults
- Treat completed plan/spec slices as done unless the docs explicitly defer follow-up work.
- Prefer a shorter “remaining todo” list over preserving every historical milestone in the master section.

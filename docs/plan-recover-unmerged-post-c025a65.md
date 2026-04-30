# Plan: recover unmerged post-c025a65 work

## Objective
Recover the intended post-`c025a65` work that was pushed to feature branches but never merged into `main`, then assemble it on one auditable recovery branch.

## Recovery scope
Recover the final intended changes from the closed/unmerged PR branches after `c025a65`, prioritizing the last validated version of each logical slice rather than replaying every abandoned intermediate attempt.

## Recovery set
- Upstream correctness carryovers
  - `34af3b4`
- Bank Rules planning + implementation + follow-up migration fixes
  - `30313fd`
  - `af72ba1`
  - `b3d436c`
  - `18aba62`
- Search / serializer / customer detail fixes
  - `d034dbd`
- Search overlay dismissal fix
  - `97a2e3a`
- Alembic compatibility placeholder for the removed bank-rules revision
  - recover once, not three duplicate times

## Constraints
- Preserve the current `main` base at `c025a65`.
- Prefer final validated commits for each slice over superseded duplicates.
- Keep the resulting branch bootable; the Alembic compatibility revision must be present.
- Verify after replaying commits because some slices touched the same frontend files.

## Implementation sketch
1. Cherry-pick the planned recovery commits onto a fresh branch from `main`.
2. Resolve overlaps where later validated commits supersede earlier failed attempts.
3. Verify:
   - git status clean
   - targeted tests from recovered slices
   - Alembic integrity test
4. Push recovery branch and open a recovery PR for review/merge.

## Risks
- Overlapping frontend changes in `app/static/js/app.js`
- Reintroducing the deleted bank-rules migration regression without its follow-up fix
- Recovering duplicate logical changes more than once

## Verification
- run targeted recovered test suites where feasible
- `git diff --check`
- inspect resulting commit log and changed file set

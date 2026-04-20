# Spec: recover unmerged post-c025a65 work

## Problem
`main` stopped at `c025a65`, while several later fixes/features were pushed to branches and then closed without merge. As a result, GitHub `main` never received those changes.

## Desired outcome
Create one recovery branch from `main` that contains the intended post-`c025a65` work so it can finally be reviewed and merged properly.

## Functional requirements
- Recovery branch must start from `c025a65`.
- Recovery branch must include:
  - upstream correctness carryovers
  - bank rules MVP plus its follow-up enum fixes
  - search/customer detail/credit note/serializer fixes
  - search overlay dismissal fix
  - Alembic compatibility placeholder for revision `o5d6e7f8g9h0`
- Recovery branch should avoid replaying superseded duplicate commits when the final validated commit already contains the intended change.

## Acceptance criteria
1. A dedicated recovery branch exists from `main`.
2. The branch contains the intended recovered commits (or their final equivalent state).
3. The branch includes the missing Alembic compatibility placeholder.
4. The branch is pushed to GitHub and available for merge review.

## Out of scope
- Automatic merge to `main` without review
- Recovering unrelated pre-`c025a65` experimental commits

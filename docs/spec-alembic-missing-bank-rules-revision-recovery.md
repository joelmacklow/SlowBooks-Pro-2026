# Spec: Alembic missing bank-rules revision recovery

## User-visible failure
Application bootstrap fails with:
- `Can't locate revision identified by 'o5d6e7f8g9h0'`

## Root cause
`main` no longer contains the Bank Rules MVP migration file, but some databases still reference that revision in `alembic_version`.

## Desired behavior
- Bootstrapping and `alembic upgrade head` on `main` should work even when a database was previously stamped with `o5d6e7f8g9h0`.

## Functional requirements
- The repository must include a migration file with revision id `o5d6e7f8g9h0`.
- That migration must not introduce the unmerged Bank Rules schema on `main`.
- The migration chain must remain linear from `n4c5d6e7f8g9` to `o5d6e7f8g9h0`.

## Out of scope
- Reintroducing Bank Rules MVP itself
- Data cleanup for already-created bank-rules tables in databases that previously ran the deleted branch
- Bootstrap script changes

## Acceptance criteria
1. The migration file `o5d6e7f8g9h0_add_bank_rules_mvp.py` exists on `main`.
2. It acts as a compatibility no-op in both upgrade and downgrade directions.
3. Migration integrity tests still pass.
4. No new app code depends on bank-rules schema in this recovery slice.

## Test plan
- Unit/integrity:
  - ensure the migration chain is still single-head
  - ensure revision `o5d6e7f8g9h0` exists
  - optionally assert the migration text advertises compatibility/no-op semantics

## Security / operational note
This is an operational recovery fix only. It changes migration discoverability, not application auth or business behavior.

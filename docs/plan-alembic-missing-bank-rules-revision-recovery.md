# Plan: Alembic missing bank-rules revision recovery

## Objective
Restore startup compatibility for environments whose database `alembic_version` points at the removed Bank Rules MVP revision `o5d6e7f8g9h0`, without reintroducing the whole unmerged Bank Rules feature onto `main`.

## Problem
- Some environments already ran the deleted Bank Rules branch migration and now store revision `o5d6e7f8g9h0` in `alembic_version`.
- Current `main` no longer ships that migration file.
- `scripts/bootstrap_database.py` always runs `alembic upgrade head`, so Alembic fails immediately when it cannot locate the stamped revision.

## Constraints
- Keep `main` behavior aligned with the currently shipped schema/features.
- Do not resurrect the full Bank Rules feature on `main`.
- Preserve a single linear migration chain.
- Recovery should be safe for both:
  - databases already stamped at `o5d6e7f8g9h0`
  - fresh databases upgrading from `n4c5d6e7f8g9`

## Recommended fix
Reintroduce a **placeholder / compatibility migration** with revision id `o5d6e7f8g9h0` and `down_revision = "n4c5d6e7f8g9"`, but make it a no-op.

### Why this works
- Databases already stamped at `o5d6e7f8g9h0` will let Alembic resolve the current revision again.
- Fresh databases can still upgrade linearly to head without picking up unmerged Bank Rules schema changes.
- Extra bank-rules tables left behind in upgraded environments remain harmless because current `main` does not reference them.

## Impacted files
- `alembic/versions/o5d6e7f8g9h0_add_bank_rules_mvp.py`
- `tests/test_alembic_migration_integrity.py`

## Acceptance criteria
- Alembic can resolve revision `o5d6e7f8g9h0` on current `main`.
- Migration integrity test still reports one linear chain and one head.
- Fresh upgrades from `n4c5d6e7f8g9` remain valid.
- No current `main` schema tables/columns are added by this recovery slice.

## Verification
- `python -m py_compile alembic/versions/o5d6e7f8g9h0_add_bank_rules_mvp.py tests/test_alembic_migration_integrity.py`
- `uv run --with pytest python -m pytest tests/test_alembic_migration_integrity.py -q`
- `git diff --check`

## Risks and mitigations
- **Risk:** Future work assumes `o5d6e7f8g9h0` carried Bank Rules schema.
  - **Mitigation:** Document clearly in the migration docstring/body that this is a compatibility placeholder on `main`.
- **Risk:** Environments that already have the old bank-rules tables may drift from code expectations.
  - **Mitigation:** Current `main` ignores those tables, so compatibility is acceptable until/unless the feature is reintroduced properly.

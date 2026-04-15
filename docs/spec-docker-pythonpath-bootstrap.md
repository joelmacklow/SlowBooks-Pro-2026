# Spec: Fix Docker bootstrap import path

## Deliverable
Update the app container configuration so `python scripts/bootstrap_database.py`
can import `app.config`.

## Rules
- The Docker image must set `PYTHONPATH=/app`.
- `scripts/bootstrap_database.py` must add the repository root to `sys.path`
  before importing from `app`.
- Tests must fail if either the Dockerfile or bootstrap script regresses on
  import resolution.
- Do not change the bootstrap command or the external database env contract.

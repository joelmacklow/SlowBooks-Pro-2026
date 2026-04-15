# Restore batch payment schema imports at app startup

## Summary
Add the missing batch-payment Pydantic schema module so FastAPI can import the
batch payments route during app startup.

## Key Changes
- Add `app/schemas/batch_payments.py` with request models that match the
  existing route and frontend payload shape.
- Add a regression test that imports the module and verifies the expected
  request fields remain present.

## Test Plan
- Run `python -m unittest tests.test_batch_payment_schema`.
- Run `git diff --check`.

## Defaults
- App startup should no longer fail on `ModuleNotFoundError` for
  `app.schemas.batch_payments`.

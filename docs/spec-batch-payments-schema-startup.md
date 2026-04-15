# Spec: Restore batch payment schema imports at app startup

## Deliverable
Add the missing batch payments schema module used by `app.routes.batch_payments`.

## Rules
- `app/schemas/batch_payments.py` must define `BatchPaymentCreate`.
- The schema must accept the payload shape already sent by the batch-payments UI.
- Tests must fail if the schema module or its key fields disappear.
- Do not change the `/api/batch-payments` route contract beyond restoring the
  missing schema.

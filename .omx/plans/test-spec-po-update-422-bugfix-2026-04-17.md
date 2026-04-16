# Test Spec — Purchase Order update 422 bugfix

## Date
2026-04-17

## Red/Green plan
- Add a Python test that reproduces the update flow against `update_po` or the FastAPI route with a realistic payload.
- Confirm the failure mode matches the reported 422.
- Fix the underlying issue with the smallest diff.
- Re-run targeted PO JS and Python tests covering update/create flows.

## Verification
- New targeted PO update bugfix test
- `node tests/js_purchase_orders_detail.test.js`
- `node tests/js_purchase_orders_create_actions.test.js`
- `node tests/js_document_email_actions.test.js`
- `git diff --check`

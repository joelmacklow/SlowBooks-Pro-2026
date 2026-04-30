# Test Spec — Invoice credit-note availability check

## Date
2026-04-17

## Red/Green plan
- Add a JS test for invoice detail showing available credit notes for the invoice customer.
- Add a JS test for applying a credit note from the invoice screen using the existing credit-memo apply endpoint.
- Re-run existing document detail/email tests to ensure no regressions.

## Verification
- `node tests/js_invoice_credit_note_availability.test.js`
- `node tests/js_document_detail_alignment.test.js`
- `node tests/js_document_email_actions.test.js`
- `git diff --check`

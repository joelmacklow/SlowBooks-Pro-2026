# Test Spec — Customer detail balance status filter follow-up

## Date
2026-04-21

## Verification
- Extend the targeted customer detail JS test with draft and void invoices.
- Verify the rendered balance card includes only `sent`/`partial` balances.
- Run:
  - `node tests/js_customer_detail_navigation.test.js`
  - `node tests/js_document_detail_alignment.test.js`
  - `node --check app/static/js/customers.js`
  - `git diff --check`

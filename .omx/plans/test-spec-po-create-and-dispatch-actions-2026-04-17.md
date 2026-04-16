# Test Spec — Purchase Order create-and-dispatch actions

## Date
2026-04-17

## Red/Green plan
- Extend PO detail JS tests to prove the new unsaved-PO actions are rendered.
- Add a focused JS test that:
  - creates a new PO via the new PDF action and verifies POST then `API.open`
  - creates a new PO via the new Email action and verifies POST then `App.showDocumentEmailModal`
- Re-run existing PO detail/email tests to ensure saved-PO behavior still works.

## Verification
- `node tests/js_purchase_orders_detail.test.js`
- `node tests/js_document_email_actions.test.js`
- any new PO action JS test added for this slice
- `git diff --check`

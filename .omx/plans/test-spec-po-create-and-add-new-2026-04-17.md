# Test Spec — Purchase Order create-and-add-new workflow

## Date
2026-04-17

## Red/Green plan
- Extend PO detail JS test to expect the new unsaved-PO labels.
- Extend the focused PO create-actions JS test to verify `Create & Add New`:
  - posts the PO
  - reloads a fresh editor context
  - navigates/stays on PO detail screen with empty/new state
- Re-run the existing PO create-dispatch and saved-PO tests to ensure no regressions.

## Verification
- `node tests/js_purchase_orders_detail.test.js`
- `node tests/js_purchase_orders_create_actions.test.js`
- `node tests/js_document_email_actions.test.js`
- `git diff --check`

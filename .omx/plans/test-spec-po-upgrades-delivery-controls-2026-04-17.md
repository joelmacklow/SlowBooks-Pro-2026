# Test Spec — Purchase Order delivery controls and document actions

## Date
2026-04-17

## Red/Green plan

### Backend tests
1. Add parser/helper tests for approved PO delivery locations from settings, including:
   - company primary address included when present
   - extra admin-managed locations included
   - blank/duplicate entries normalized out
2. Add purchase order route tests proving:
   - approved delivery-location endpoint requires purchasing access and returns approved locations
   - create/update PO accepts approved `ship_to`
   - create/update PO rejects unapproved `ship_to` with 400
3. Keep document email route coverage intact and add any route assertions needed for PO PDF/email actions only if backend changes require it.

### Frontend tests
1. Update PO detail JS test to expect delivery-location selection UI instead of free-form textarea.
2. Add/extend JS tests to prove:
   - approved delivery locations are loaded into PO editor context
   - detail screen shows Print / PDF and Email actions for saved POs
   - clicking Print / PDF opens the PO PDF endpoint
   - email action still targets vendor email
3. Update settings JS tests or add a new one to cover the admin-only approved-location field if needed.

## Verification suite
- Targeted JS tests:
  - `tests/js_purchase_orders_detail.test.js`
  - `tests/js_document_email_actions.test.js`
  - any new PO/settings JS test added for this slice
- Targeted Python tests:
  - PO route/unit tests added for approved delivery locations
  - existing document email/PDF tests touched by the change
- Safety checks:
  - `python -m pytest ...`
  - `node ...` targeted JS tests
  - `git diff --check`

## Risks to watch
- Purchasing users currently load `/settings`; this slice should remove that dependency for PO editing.
- Settings storage uses string values; delivery-location serialization/parsing must stay compact and robust.
- Existing POs may already store legacy free-text destinations; rendering should tolerate old values while new saves stay restricted.

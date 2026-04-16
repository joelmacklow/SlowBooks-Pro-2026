# Test Spec — Bills page Purchase Order link navigation bugfix

## Date
2026-04-17

## Red/Green plan
- Add a JS test that renders or invokes the Bills page PO action for a bill with `po_id` and proves it navigates to the PO route.
- Confirm the test fails against current behavior.
- Apply the smallest UI fix.
- Re-run targeted Bills/PO navigation tests.

## Verification
- New targeted Bills PO-link JS test
- Any existing Bills/PO JS tests touched by the change
- `git diff --check`

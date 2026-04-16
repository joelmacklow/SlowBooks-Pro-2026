# Test Spec — Vendor-assigned items for purchase orders

## Date
2026-04-17

## Red/Green plan
- Add Python tests covering item vendor assignment persistence and items API vendor filtering.
- Add JS tests covering:
  - item/service modal vendor field rendering and payload submission
  - PO editor vendor-specific item filtering and refresh behavior
- Confirm tests fail first.
- Implement the smallest model/schema/route/UI change set to pass.
- Re-run targeted item/PO tests and safety checks.

## Verification
- New/updated Python tests for item vendor assignment + filtering
- New/updated JS tests for items modal and PO vendor filtering
- Existing PO/item JS tests touched by the change
- `git diff --check`

# Test Spec: mark Bank Rules MVP complete

## Acceptance criteria
- `docs/localization_summary.md` no longer lists Bank Rules MVP as an active pending priority.
- The Remaining Todo narrative records Bank Rules MVP as completed shared banking infrastructure.
- Budget vs Actual is promoted to the first active next slice.
- Later pending slices remain in the same relative order.

## Verification
1. Inspect the active next-slices section and confirm there is no pending Bank Rules MVP item.
2. Confirm the text references completed bank-rule infrastructure instead of implying missing implementation.
3. Run `git diff --check`.

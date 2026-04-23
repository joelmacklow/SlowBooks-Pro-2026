# Fixed Assets Edit Details Button Bugfix Specification

## Goal
Ensure the fixed-asset detail page Edit details button opens the correct asset edit form.

## Required Behavior
- Clicking Edit details must open the edit form for the current asset id.
- The detail screen should keep using the modal edit flow.
- No other detail-page actions should change.

## Constraints
- Do not convert the detail edit flow into a separate route in this slice.
- Do not alter asset save behavior beyond fixing the button wiring.

## Verification
- Targeted fixed-assets UI regression coverage.
- `node --check app/static/js/fixed_assets.js`
- `git diff --check`

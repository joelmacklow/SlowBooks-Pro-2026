# Fixed Assets Edit Details Modal Runtime Fix Specification

## Goal
Ensure the Edit details button on fixed-asset detail pages either opens the modal or shows a visible error.

## Required Behavior
- Clicking Edit details must invoke the asset edit modal asynchronously.
- If modal setup fails, the user should get an error toast instead of a silent no-op.
- Existing successful edit behavior must remain unchanged.

## Constraints
- Do not change the route structure or replace the modal flow.
- Keep the fix focused on the button/helper path.

## Verification
- Targeted fixed-assets UI regression coverage for success and failure paths.
- `node --check app/static/js/fixed_assets.js`
- `git diff --check`

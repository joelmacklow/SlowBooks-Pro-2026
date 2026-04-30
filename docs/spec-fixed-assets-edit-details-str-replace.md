# Fixed Assets Edit Details String Rendering Fix Specification

## Goal
Ensure the fixed-asset edit modal renders correctly when asset fields contain numeric values.

## Required Behavior
- Opening Edit details must not throw `str.replace is not a function`.
- Numeric, null, and empty values should be safely converted before HTML escaping.
- Existing edit-modal content and field values should otherwise remain unchanged.

## Constraints
- Do not change the modal workflow or backend payload shape.
- Keep the fix focused on frontend rendering safety.

## Verification
- Targeted fixed-assets UI regression coverage with a real `escapeHtml`-style implementation.
- `node --check app/static/js/fixed_assets.js`
- `git diff --check`

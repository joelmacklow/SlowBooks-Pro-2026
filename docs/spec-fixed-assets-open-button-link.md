# Fixed Assets Open Button Link Bugfix Specification

## Goal
Ensure the Registered Assets Open action consistently opens the selected fixed asset detail page.

## Required Behavior
- Clicking Open should navigate to `#/fixed-assets/detail?id=<assetId>`.
- The detail origin should be recorded so Back returns to the fixed-assets register.
- The asset name should remain non-clickable.

## Constraints
- Do not restore the old asset-name hyperlink.
- Do not change detail-page content or permissions.

## Verification
- Targeted fixed-assets UI regression coverage.
- `node --check app/static/js/fixed_assets.js`
- `git diff --check`

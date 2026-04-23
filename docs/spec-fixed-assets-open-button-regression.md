# Fixed Assets Open Button Regression Specification

## Goal
Ensure inline fixed-asset row actions resolve in the browser after the helper-based refactor.

## Required Behavior
- The Registered Assets Open button must resolve `FixedAssetsPage.openAssetDetail(...)` in the browser.
- The helper-based row/detail actions should remain available through the browser global.
- No other fixed-asset navigation behavior should change.

## Constraints
- Do not reintroduce the asset-name hyperlink.
- Do not replace the helper-based approach with duplicated inline navigation strings.

## Verification
- Targeted fixed-assets UI regression coverage.
- `node --check app/static/js/fixed_assets.js`
- `git diff --check`

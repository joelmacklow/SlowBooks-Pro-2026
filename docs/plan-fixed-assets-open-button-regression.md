# Fixed Assets Open Button Regression Plan

## Objective
Restore the Registered Assets Open action so it works reliably in the browser after the recent helper refactor.

## Constraints
- Keep the asset name plain text and keep Open as the only row navigation affordance.
- Limit the fix to client-side action binding for the fixed-assets page.

## Implementation Sketch
- Expose `FixedAssetsPage` on the browser global so inline `onclick` handlers can resolve helper methods reliably.
- Extend the UI regression test to assert the page object is globally available for inline handlers.

## Impacted Files
- `app/static/js/fixed_assets.js`
- `tests/js_fixed_assets_ui.test.js`

## Test Plan
- Run the targeted fixed-assets UI test.
- Run a JS syntax check and `git diff --check`.

## Risk Notes
- Without a global binding, inline row actions can silently fail even though direct unit calls still pass.

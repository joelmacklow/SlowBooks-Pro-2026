# Fixed Assets Open Button Link Bugfix Plan

## Objective
Make the Registered Assets table's Open action reliably navigate to the fixed-asset detail screen.

## Constraints
- Keep the asset name as plain text and preserve the Open action as the single row navigation affordance.
- Limit the slice to the fixed-assets list/detail navigation path.

## Implementation Sketch
- Route the Open button through a dedicated helper that sets the detail origin and navigates to the detail hash.
- Update the UI regression test to assert the rendered Open action uses the helper.

## Impacted Files
- `app/static/js/fixed_assets.js`
- `tests/js_fixed_assets_ui.test.js`

## Test Plan
- Run the targeted fixed-assets UI test.
- Run a JS syntax check and `git diff --check`.

## Risk Notes
- Navigation regressions here would make the detail page effectively unreachable from the register.

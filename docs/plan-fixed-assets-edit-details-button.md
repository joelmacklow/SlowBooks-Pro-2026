# Fixed Assets Edit Details Button Bugfix Plan

## Objective
Make the fixed-asset detail screen's Edit details button reliably open the asset edit form.

## Constraints
- Keep the detail view modal-edit pattern intact.
- Limit the slice to the detail-page edit action wiring.

## Implementation Sketch
- Route the detail-page Edit details action through a dedicated helper instead of embedding the async form call inline.
- Extend the fixed-assets UI regression test to assert the button uses the helper and that the helper forwards the asset id to the edit form.

## Impacted Files
- `app/static/js/fixed_assets.js`
- `tests/js_fixed_assets_ui.test.js`

## Test Plan
- Run the targeted fixed-assets UI test.
- Run a JS syntax check and `git diff --check`.

## Risk Notes
- If the helper is wired incorrectly, the detail page loses its only edit entry point.

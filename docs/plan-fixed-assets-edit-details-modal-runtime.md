# Fixed Assets Edit Details Modal Runtime Fix Plan

## Objective
Make the fixed-asset detail Edit details action open the modal reliably and surface any fetch/render failure instead of failing silently.

## Constraints
- Keep the modal edit workflow intact.
- Limit the fix to the client-side action wrapper for the Edit details button.

## Implementation Sketch
- Make the Edit details helper async and wrap the modal-opening call in try/catch.
- Report failures through the existing toast mechanism so browser/runtime issues are visible.
- Extend the UI regression test to cover both the happy path and the error path.

## Impacted Files
- `app/static/js/fixed_assets.js`
- `tests/js_fixed_assets_ui.test.js`

## Test Plan
- Run the targeted fixed-assets UI test.
- Run a JS syntax check and `git diff --check`.

## Risk Notes
- Without error handling, async modal setup failures can appear as a dead button to users.

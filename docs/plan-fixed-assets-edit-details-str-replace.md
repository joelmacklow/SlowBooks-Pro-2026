# Fixed Assets Edit Details String Rendering Fix Plan

## Objective
Fix the fixed-asset edit modal so numeric field values do not crash rendering with `str.replace is not a function`.

## Constraints
- Keep the existing modal form structure intact.
- Limit the fix to type-safe rendering of form field values.

## Implementation Sketch
- Add a small helper inside `fixed_assets.js` that converts nullable values to strings before passing them into `escapeHtml`.
- Update the asset form to use that helper for numeric/date-backed fields.
- Strengthen the UI regression test so `escapeHtml` behaves like the real browser helper and catches non-string regressions.

## Impacted Files
- `app/static/js/fixed_assets.js`
- `tests/js_fixed_assets_ui.test.js`

## Test Plan
- Run the targeted fixed-assets UI test.
- Run a JS syntax check and `git diff --check`.

## Risk Notes
- Any remaining raw numeric values passed to `escapeHtml` can still break other modal fields if not normalized consistently.

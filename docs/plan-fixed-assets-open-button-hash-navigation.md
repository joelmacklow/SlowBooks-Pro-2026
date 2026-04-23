# Fixed Assets Open Button Hash Navigation Fix Plan

## Objective
Fix the programmatic navigation path so the fixed-assets Open action reaches the detail page with the correct `id` query parameter.

## Constraints
- Keep Open as the only row navigation affordance.
- Limit the functional change to client-side navigation/hash handling.

## Implementation Sketch
- Update `App.navigate` so programmatic route changes also synchronize `location.hash`, matching the existing nav-link behavior.
- Add a regression test that proves `App.navigate('#/...?...')` updates the browser hash before rendering.

## Impacted Files
- `app/static/js/app.js`
- `tests/js_app_hash_routing.test.js`

## Test Plan
- Run the app hash-routing regression test.
- Re-run the fixed-assets UI test.
- Run JS syntax checks and `git diff --check`.

## Risk Notes
- Programmatic navigation is shared broadly, so the fix must avoid triggering duplicate renders or redirect loops.

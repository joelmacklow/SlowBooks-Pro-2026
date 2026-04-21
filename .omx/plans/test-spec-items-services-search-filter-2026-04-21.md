# Test Spec — Items & Services search filter

## Date
2026-04-21

## Verification
- Add/update JS coverage for the item list page to assert:
  - search input renders
  - search term is passed to `/items?search=...`
  - matching items render and non-matching ones do not
  - empty search result state renders
- Run targeted JS tests for the Items page.
- Run `node --check app/static/js/items.js`.
- Run `git diff --check`.

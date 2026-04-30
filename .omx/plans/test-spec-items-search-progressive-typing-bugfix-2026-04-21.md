# Test Spec — Items search progressive typing bugfix

## Date
2026-04-21

## Verification
- Extend the targeted items search JS test to simulate successive search values (`P`, `Pe`, etc.).
- Assert each step calls the expected `/items?search=...` endpoint and keeps rendering updated results.
- Run:
  - `node tests/js_items_search_filter.test.js`
  - `node tests/js_items_vendor_assignment.test.js`
  - `node --check app/static/js/items.js`
  - `git diff --check`

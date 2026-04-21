# PRD — Items & Services search filter

## Date
2026-04-21

## Objective
Add a search/filter workflow to the Items & Services page so users can quickly locate items once a large number of products or services exist.

## Current-state evidence
- `app/static/js/items.js:10-42` renders the Items & Services page as a plain table with no filter/search controls.
- `app/routes/items.py:13-32` already supports a `search` query param that filters by item name or code.
- Existing item UI tests focus on form/edit behavior (`tests/js_items_vendor_assignment.test.js`) and do not cover list discovery/filtering.

## Problem
When the item catalog grows, the current page forces users to visually scan the full table. The backend already exposes a search hook, but the UI does not surface it.

## Requirements
- Add a visible search/filter control to the Items & Services page.
- Allow users to locate items by at least code and name.
- Preserve the current table layout and item edit actions.
- Keep the implementation lightweight and aligned with the existing vanilla SPA pattern.

## Recommended approach
- Add a toolbar search input to `ItemsPage.render()`.
- Use the existing backend `search` query param so filtering scales beyond tiny client-only lists.
- Trigger filtering on input/change with a small stateful render helper so the page can re-query as the search term changes.
- Preserve the empty state but distinguish between “no items yet” and “no items match this search”.

## Acceptance criteria
1. The Items & Services page shows a search input in the toolbar.
2. Typing a code or item name filters the visible results.
3. Clearing the search restores the full item list.
4. Existing New Item and Edit actions still work.
5. Empty search results show a clear “no matches” state.

## Risks
- Over-eager querying on every keystroke could create noisy API traffic if not slightly debounced or state-managed.
- The backend search currently covers code and name only, so users may still expect description filtering unless copy clarifies behavior.

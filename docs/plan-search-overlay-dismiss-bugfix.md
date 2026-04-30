# Plan: Search overlay dismiss bugfix

## Objective
Ensure the global search results overlay reliably disappears after a user clicks any search result.

## Problem
- Search result clicks call `closeSearchDropdown()`, but the current global-search flow can still re-show the overlay after the click if a delayed/in-flight search response resolves afterward.

## Scope
- Search overlay dismissal behavior only
- No search ranking or navigation target changes in this slice

## Impacted files
- `app/static/js/app.js`
- `app/static/js/utils.js`
- `tests/js_global_search_navigation.test.js`

## Implementation sketch
1. Add an App-level search-dismiss helper that:
   - clears the pending timeout
   - invalidates in-flight search render attempts
   - hides the dropdown
   - clears the search input
2. Update global search rendering to only show results if the response still belongs to the active request and the input still matches the query.
3. Put dismissal first in result click handlers so the overlay hides before navigation logic runs.
4. Add an explicit close control inside the search overlay as a fallback UX path.
5. Make `closeSearchDropdown()` delegate to the App-level helper when available.
6. Add JS regression tests for stale-response dismissal and close-control rendering.

## Acceptance criteria
- Clicking any search result hides the overlay immediately.
- The overlay includes a visible close control.
- A stale async search response cannot re-open the overlay after dismissal.
- Existing search result navigation remains unchanged.

## Verification
- `node tests/js_global_search_navigation.test.js`
- `git diff --check`

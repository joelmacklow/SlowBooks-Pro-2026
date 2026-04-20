# Spec: Search overlay dismiss bugfix

## User-visible bug
After clicking a global search result, the search results overlay sometimes remains visible or reappears.

## Desired behavior
- The overlay should disappear when the user clicks a result.
- It should stay dismissed even if an older async search request resolves afterward.

## Functional requirements
- Dismissing search results must invalidate older pending search render attempts.
- Hiding the overlay must also clear any pending timeout for delayed search execution.
- Search result navigation behavior must remain unchanged.

## Out of scope
- Search result ranking
- New search sections
- Search keyboard navigation

## Test plan
- JS test proving:
  - dismiss helper hides overlay
  - stale response cannot re-open overlay after dismissal

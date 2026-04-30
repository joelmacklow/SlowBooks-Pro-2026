# COA Favorites Watchlist Specification

## Goal
Allow chart-of-accounts entries to be marked as dashboard favorites and surface those favorites in the dashboard watchlist widget.

## Required Behavior
- Accounts must expose a persistent boolean flag indicating whether they are a dashboard watchlist favorite.
- Account managers must be able to view and edit that flag from the chart-of-accounts UI.
- When one or more active accounts are flagged as favorites, the dashboard watchlist widget should show those favorites (up to the existing limit), even if some have zero activity for the current month/YTD window.
- When no favorite accounts are flagged, the dashboard should keep the existing auto-generated watchlist behavior.

## Constraints
- Keep the dashboard API shape broadly compatible with the current widget.
- Do not change dashboard permissions, widget ordering, or add a new module/page.
- Do not introduce new packages or a new chart/watchlist subsystem.

## Verification
- Targeted JS tests for account list/form rendering and dashboard widget rendering.
- Targeted Python tests for favorite-driven watchlist results and fallback behavior.
- `node --check app/static/js/app.js`
- `git diff --check`

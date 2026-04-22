# COA Favorites Watchlist Plan

## Objective
Let users flag individual chart-of-accounts entries as dashboard favorites and show those favorites in the Company Snapshot watchlist widget.

## Constraints
- Keep the existing dashboard widget layout and permissions intact.
- Do not add dependencies or replace the current dashboard data flow.
- Preserve a useful watchlist when no favorites have been flagged yet.

## Implementation Sketch
- Add a persistent boolean favorite flag to accounts, expose it through account create/update/read schemas, and add an Alembic migration.
- Update the chart-of-accounts UI so managers can see and edit the dashboard favorite flag.
- Teach dashboard watchlist generation to prefer flagged favorites, including zero-activity favorites, while falling back to the existing auto-watchlist behavior when none are selected.
- Add backend and frontend regression coverage for favorite persistence/rendering and watchlist output.

## Impacted Files
- `alembic/versions/*_add_dashboard_favorite_flag_to_accounts.py`
- `app/models/accounts.py`
- `app/schemas/accounts.py`
- `app/routes/accounts.py`
- `app/services/dashboard_metrics.py`
- `app/static/js/app.js`
- `tests/test_dashboard_snapshot_metrics.py`
- `tests/js_accounts_actions.test.js`
- `tests/js_dashboard_rbac_visibility.test.js`

## Test Plan
- Add/update failing tests first where practical for account UI rendering and dashboard watchlist favorite behavior.
- Run targeted JS tests for accounts/dashboard render paths.
- Run targeted Python dashboard metric tests and migration-integrity checks if needed.
- Finish with `git diff --check`.

## Risk Notes
- A global watchlist logic change could hide current auto-selected accounts if the fallback behavior is not preserved.
- Checkbox/form serialization is easy to get wrong in the current plain-JS account form, so boolean coercion must be explicit.

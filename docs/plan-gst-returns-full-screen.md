# Move GST Returns to a dedicated full-screen workflow

## Summary
Replace the GST Return modal with a dedicated GST Returns screen under Reports,
including a separate detail screen with summary and transactions tabs.

## Key Changes
- Add a GST Returns main screen that lists open/current periods and historical
  confirmed returns.
- Add a GST return detail screen with:
  - a `GST Return` summary tab
  - a `Transactions` tab with server pagination
- Remove the source-drilldown table from the summary tab.
- Replace the lower part of the main screen with historical returns grouped by
  financial year.
- Reuse existing confirmed GST settlements as the v1 historical source.

## Test Plan
- Add backend tests for GST overview/history and paginated transactions.
- Add frontend JS tests for:
  - navigating from the Report Center card to the GST Returns screen
  - rendering historical returns
  - rendering/paging the transactions tab
- Run focused Python and JS tests plus `git diff --check`.

## Defaults
- GST stays under Reports; no new sidebar item.
- Transactions use server-side pagination with explicit page controls.
- Historical returns means confirmed/settled GST periods only.

# PRD — Dashboard FY profit and invoice list overdue follow-up

## Date
2026-04-21

## Objective
Refine the newly refreshed dashboard and invoice list so they better match NZ accounting workflows and the invoice list reference (`../tmp/InvoiceList.png`).

## Problem
- The dashboard profit widget currently behaves like calendar-year YTD, but the user wants the current financial year instead.
- The invoice list is still a simple unsorted table with only basic status filtering.
- The invoice reference shows useful operational signals missing from SlowBooks: overdue-day visibility, reminder state, paid-vs-due values, and clearer overdue styling.

## Requirements
- Profit summary on the Company Snapshot must use the current financial year, not the calendar year.
- If company settings define `financial_year_start` / `financial_year_end`, use those boundaries; otherwise keep a sensible fallback.
- The invoice list must support column sorting.
- The invoice status filter must include an explicit `Overdue` option.
- The invoice list must show at least:
  - overdue-by days
  - paid amount
  - due/balance amount
  - reminders summary
- Due dates should render in a danger/red style when the invoice is overdue.

## Approach
- Extend dashboard metrics to compute current-FY boundaries from company settings.
- Extend invoice response payloads with overdue/reminder metadata needed by the list view.
- Refactor the invoice list renderer into stateful filter/sort helpers rather than one static loop.
- Keep sorting/filtering client-side on the fetched invoice list to minimize API shape churn.

## Impacted files
- `app/services/dashboard_metrics.py`
- `app/routes/invoices.py`
- `app/schemas/invoices.py`
- `app/static/js/invoices.js`
- `app/static/css/style.css`
- invoice/dashboard JS tests
- targeted backend tests for dashboard FY and invoice response metadata

## Acceptance criteria
1. Dashboard profit period tracks the active financial year from settings when configured.
2. Invoice list supports sorting by clicking columns.
3. Invoice filter dropdown includes `Overdue`, and selecting it shows only overdue unpaid invoices.
4. Invoice rows display overdue-by days and a reminders summary.
5. Overdue due dates render in red/danger styling.
6. Existing invoice open/send actions still work.

## Risks
- Financial-year boundary logic could drift from the settings contract if boundary parsing is duplicated.
- Invoice reminder metadata could introduce N+1 query behavior if assembled naively.
- Client-side sorting must preserve existing row actions and not break detail navigation.

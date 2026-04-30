# PRD — Customer detail balance bugfix

## Date
2026-04-21

## Objective
Fix the Customer detail page balance card so it reflects the outstanding balance from all invoices not marked as paid.

## Current-state evidence
- `app/static/js/customers.js:64-72` loads the customer record plus invoice list separately for the detail page.
- `app/static/js/customers.js:112-116` currently renders the balance card from `customer.balance`.
- The detail view already has the invoice list in memory, including each invoice `status` and `balance_due`.

## Problem
The customer detail balance card can be wrong when the stored `customer.balance` value is stale or does not match the actual outstanding invoice balances. The detail page should instead derive the displayed balance from the invoice list it already fetches.

## Requirements
- Compute the customer detail balance from the loaded invoices on the detail page.
- Include all invoice balances where the invoice is **not** marked `paid`.
- Preserve the rest of the customer detail page behavior and layout.

## Acceptance criteria
1. The balance card on customer detail equals the sum of `balance_due` for all loaded invoices whose status is not `paid`.
2. Paid invoices do not contribute to the balance card.
3. Existing customer detail navigation and history sections still render.

## Risks
- If invoice status/balance data is inconsistent, the UI-derived total may differ from stored customer summary fields elsewhere.
- The fix should stay scoped to the detail page and not silently change unrelated customer list balances.

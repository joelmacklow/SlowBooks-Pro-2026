# PRD — Invoice credit-note availability check

## Date
2026-04-17

## Problem
Credit memos can already be applied to invoices from the credit-memo side, but the invoice workflow does not surface whether a customer has available credit notes that could be applied against the current invoice.

## Goal
Expose available customer credit notes from the invoice detail workflow and allow applying them to the invoice from that screen.

## Requirements
- When viewing/editing an invoice for a customer, check for issued credit notes with remaining balance for that same customer.
- Show an invoice-side credit-note availability section when applicable.
- Allow applying an available credit note against the current invoice from the invoice screen.
- Only show apply actions when the invoice has an id and a remaining balance.
- Preserve existing credit-memo application behavior and invoice actions.

## Non-goals
- Reworking the underlying accounting logic for credit application.
- Supporting credit application before an invoice is saved.
- Rebuilding the entire credit-memo workflow.

## Acceptance criteria
1. An existing invoice with customer credit available shows the available credit note(s) and remaining amount.
2. Applying from the invoice screen posts to the existing credit-memo application endpoint.
3. The invoice detail screen refreshes after applying credit.
4. New/unsaved invoices do not offer credit application actions until saved.

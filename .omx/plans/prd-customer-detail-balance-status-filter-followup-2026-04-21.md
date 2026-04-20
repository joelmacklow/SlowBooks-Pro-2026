# PRD — Customer detail balance status filter follow-up

## Date
2026-04-21

## Objective
Refine the customer detail balance bugfix so the balance card excludes draft and void invoices in addition to paid invoices.

## Problem
The current detail-page calculation now uses invoice balances, but it still counts draft or void invoices. The balance should represent outstanding posted debt only.

## Requirements
- Include invoice balances only for invoices that are neither `paid`, `draft`, nor `void`.
- Preserve the rest of the customer detail behavior.

## Acceptance criteria
1. `sent` and `partial` invoice balances contribute to the balance card.
2. `paid`, `draft`, and `void` invoices do not contribute.
3. Existing customer detail history rendering still works.

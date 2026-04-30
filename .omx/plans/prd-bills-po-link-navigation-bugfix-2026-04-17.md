# PRD — Bills page Purchase Order link navigation bugfix

## Date
2026-04-17

## Problem
When a bill is linked to a purchase order, the Bills page shows a Purchase Order link/action, but clicking it does not navigate to the purchase-order screen.

## Goal
Restore working navigation from a bill to its source purchase order.

## Requirements
- Reproduce the inactive PO link behavior with an automated UI test.
- Fix the Bills page so clicking the PO link navigates to the purchase-order page/detail workflow.
- Preserve existing bill actions and permissions.
- Keep the implementation minimal and aligned with current SPA routing patterns.

## Acceptance criteria
1. A bill linked to a PO renders a clickable action/link.
2. Clicking that action navigates to the PO page/detail flow.
3. Existing bills page behavior remains intact.

# PRD — Align document detail layouts with purchase-order workflow

## Date
2026-04-17

## Problem
Purchase Orders now use a full-page detail workflow with a consistent header, actions, totals panel, and create/update affordances. Invoices, estimates, and credit memos still rely on older modal-centric flows, so related documents feel inconsistent and slower to work with.

## Goal
Refactor document entry/view flows so invoices, estimates, and credit memos follow the same full-page detail-layout and action-button pattern as purchase orders.

## Scope
- Invoices
- Estimates
- Credit memos
- Any closely related document routes/buttons that need alignment to keep the workflow coherent

## Requirements
- Add dedicated detail routes/screens for invoices, estimates, and credit memos.
- Preserve current document-specific actions (email, PDF, convert, duplicate, void, mark sent, etc.) while relocating them into the PO-style detail action area.
- Keep create/update behavior intact.
- Prefer reuse of the PO detail-screen patterns over new abstractions.
- Keep list pages functional and use them as entry points into the new detail screens.

## Non-goals
- Rewriting unrelated customer/vendor/item modals.
- Reworking backend document models beyond what the UI flow needs.
- Major visual redesign beyond alignment to the existing PO pattern.

## Acceptance criteria
1. Invoices, estimates, and credit memos open in dedicated detail pages instead of edit/view modals.
2. Each aligned screen has a PO-style page header, back button, form sections, totals panel, and action buttons.
3. Existing document-specific actions remain available and functional in the aligned layouts.
4. Lists still provide clear access to new/edit existing documents.
5. Existing document behavior is preserved under regression tests.

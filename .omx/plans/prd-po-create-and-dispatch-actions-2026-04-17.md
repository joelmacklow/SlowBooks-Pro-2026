# PRD — Purchase Order create-and-dispatch actions

## Date
2026-04-17

## Problem
The PO detail screen exposes Print/PDF and Email buttons, but for a brand-new PO those actions are disabled until the user manually creates the PO first. That adds an extra step to a common dispatch workflow.

## Goal
Allow a user creating a new purchase order to click a single action that both creates the PO and then immediately opens either the PDF or the email flow.

## Requirements
- For unsaved POs, provide one-click actions that create the PO and then:
  - open the PO PDF, or
  - open the PO email modal prefilled from the vendor email.
- Existing saved-PO actions should keep working.
- Standard Create/Update should still work.
- After create-and-dispatch, the detail screen should reflect the newly created PO state rather than dropping the user back into an unsaved form.

## Acceptance criteria
1. New PO screen shows create-and-dispatch actions for PDF and email.
2. Clicking create-and-PDF posts the PO, then opens `/purchase-orders/{id}/pdf`.
3. Clicking create-and-email posts the PO, then opens the PO email modal using the created PO/vendor data.
4. Existing saved PO Email/PDF actions remain functional.

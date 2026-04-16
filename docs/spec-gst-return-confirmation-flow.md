# Spec: persist GST return confirmation before settlement/download

## Goal
Ensure GST return adjustments and confirmed box values are stored permanently before download/settlement, so the GST return workflow no longer depends on transient UI state.

## Required Behavior
- Users can edit Box 9 and Box 13 adjustments for an open GST period and refresh the summary to see the updated box list.
- Users can confirm the GST return for a period, which stores a permanent snapshot containing:
  - period dates and due date
  - GST basis/period metadata
  - Box 5–15 values
  - output/input/net GST
  - Box 9 and Box 13 adjustments
  - confirmation timestamp/status
- Once confirmed, the detail view must read from the saved return snapshot instead of recalculating from query params.
- The GST101A download path must use the saved confirmed return snapshot for confirmed periods.
- Historical Returns must include confirmed GST returns even when they have not yet been bank-settled.
- Legacy historical periods already represented only by `gst_settlements` must remain visible.

## Interface Changes
- Add a persisted GST return model/table for confirmed returns.
- Add a return-confirmation API endpoint under the GST report surface.
- Extend GST report responses with confirmation-state metadata so the UI can show confirm/download affordances correctly.

## Verification
- Targeted GST report/overview/settlement backend tests.
- GST UI test covering confirm-then-download flow.
- Full suite and `git diff --check`.

## Assumptions
- Confirmed GST returns are immutable; changing Box 9/13 later requires a future amendment workflow, not in-place editing.
- Settlement remains a separate later action, but uses the confirmed return as the authoritative snapshot when one exists.

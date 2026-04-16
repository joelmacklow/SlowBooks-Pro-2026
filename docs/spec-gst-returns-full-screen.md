# Spec: Move GST Returns to a dedicated full-screen workflow

## Deliverable
Add a dedicated GST Returns screen and detail flow to replace the current modal.

## Rules
- The Report Center GST card must open a full-screen GST workflow, not a modal.
- The detail view must have `GST Return` and `Transactions` tabs.
- The Transactions tab must use server-side pagination.
- The main GST screen must show historical returns grouped by financial year.
- Historical returns must be sourced from confirmed GST settlements in v1.

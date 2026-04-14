# Posting Lifecycle Hardening Specification

## Goal
Make posted bills and credit memos behave like invoices already do: totals-affecting edits must keep journals and balances correct, and ambiguous edits must be rejected instead of silently leaving stale postings.

## Required Behavior
- Bills:
  - `PUT /api/bills/{bill_id}` must exist.
  - Editing a posted bill's lines or posting date must reverse the old journal and create a replacement journal when the bill has no payments applied.
  - Editing bill metadata such as notes, due date, terms, ref number, or bill number must not create reversal/repost entries.
  - Financial edits must be rejected once `amount_paid > 0` or payment allocations exist.
- Credit memos:
  - `PUT /api/credit-memos/{cm_id}` must exist.
  - Editing an unapplied issued credit memo's lines or posting date must reverse the old journal and create a replacement journal.
  - Editing notes or other non-financial metadata must not rebuild the journal.
  - Financial edits must be rejected once any credit application exists or `amount_applied > 0`.
- Any reversal-producing edit must respect closing-date enforcement for both the original posting date and the new posting date.
- Voided bills and voided credit memos remain non-editable.

## Constraints
- No schema changes unless implementation proves one is strictly necessary.
- Keep downstream payment/application records unchanged; block ambiguous edits instead of attempting cascade rewrites.
- Reuse shared accounting reversal helpers instead of introducing a second posting model.

## Verification
- Backend tests for repost, metadata-only edits, payment/application blocking, and closing-date rejection.
- Full Python and JS suites, Python syntax compile, and `git diff --check`.

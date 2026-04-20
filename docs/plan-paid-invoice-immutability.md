# Plan: paid invoices are immutable

## Objective
Prevent paid invoices from being edited, updated, or voided in line with accounting best practice.

## Current state summary
- Backend invoice update blocks only void invoices, not paid invoices (`app/routes/invoices.py:218-299`).
- Backend invoice void blocks only already-void invoices, not paid invoices (`app/routes/invoices.py:316-342`).
- Invoice detail UI still renders editable fields and update/void actions for existing invoices without a paid-state guard (`app/static/js/invoices.js`, detail form/actions block).
- Invoice send already guards for draft-only status (`app/routes/invoices.py:345-356`), so status-specific action gating already exists in this module.

## Constraints
- Preserve current draft/sent/partial flows.
- Do not regress payment-applied invoice behavior outside the new paid guard.
- Keep the fix small and reversible: status guards in route/UI, not a wider invoice workflow redesign.

## Implementation sketch
1. Add backend guards rejecting `update_invoice` and `void_invoice` when status is `paid`.
2. Make paid invoice detail read-only in the UI and remove update/void actions.
3. Add regression coverage for both backend and JS detail rendering.

## Acceptance criteria
- Paid invoices cannot be updated via API.
- Paid invoices cannot be voided via API.
- Paid invoice detail does not offer edit/update/void actions.
- Non-paid invoice behavior is unchanged.

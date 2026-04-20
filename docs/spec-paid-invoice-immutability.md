# Spec: paid invoices are immutable

## Requirements summary
Once an invoice is paid, users should not be able to edit, update, or void it.

## Functional requirements
- `PUT /api/invoices/{id}` rejects paid invoices.
- `POST /api/invoices/{id}/void` rejects paid invoices.
- Paid invoice detail renders read-only and hides mutable actions.

## File-level notes
- `app/routes/invoices.py` — add paid-status guards.
- `app/static/js/invoices.js` — disable/hide mutable controls for paid invoices.
- tests — add backend and JS regression coverage.

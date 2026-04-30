# Test Spec — Document detail layout alignment

## Date
2026-04-17

## Red/Green plan
- Add JS tests for app routing to dedicated detail screens for invoices, estimates, and credit memos.
- Add/update JS tests to assert PO-style layout/action expectations on the new detail screens.
- Lock current document actions that must survive the refactor (PDF, email, convert, duplicate, void, etc.).
- Confirm tests fail first against the modal-based flows.
- Implement the smallest coherent refactor to pass.

## Verification
- New/updated JS tests for invoices, estimates, credit memos, and app routing
- Existing document email/PDF/action JS tests
- `git diff --check`

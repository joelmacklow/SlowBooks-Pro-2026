# Test Spec — Customer detail balance bugfix

## Date
2026-04-21

## Verification
- Update the customer detail JS test to cover:
  - stale `customer.balance` value from the customer payload
  - multiple invoices with `sent`, `partial`, and `paid` states
  - rendered balance card equals the sum of non-`paid` invoice balances
- Run the targeted customer detail JS test.
- Run related customer/document detail regression JS tests if needed.
- Run `git diff --check`.

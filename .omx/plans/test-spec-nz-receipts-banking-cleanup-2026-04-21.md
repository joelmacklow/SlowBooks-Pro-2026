# Test Spec — NZ receipts, undeposited funds, batch payments, and register cleanup

## Date
2026-04-21

## Verification targets

### Phase 1 — copy/method/default cleanup
- JS tests for payments, deposits, batch payments, and app navigation:
  - receive-payment methods use NZ-relevant values
  - deposit flow copy is cash/receipt-clearing oriented
  - register screen/nav label uses Bank Register (or chosen replacement)
  - batch-payments visibility/label matches the chosen product decision

### Phase 2 — method-aware workflows
- Backend tests for payment creation/deposit pending behavior:
  - cash receipts land in receipt clearing by default
  - EFT/EFTPOS defaults do not use Undeposited Funds
  - pending-deposit queries only surface receipt-clearing items

### Phase 3 — reconciliation-led electronic receipts
- Banking/reconciliation tests covering:
  - invoice matching from bank statement lines
  - avoidance of duplicate receipt posting
  - merchant-clearing follow-up tests if that slice is approved

## Safety checks
- targeted JS tests for `payments.js`, `deposits.js`, `batch_payments.js`, `check_register.js`, `app.js`
- targeted Python tests for routes/services touched by the cleanup
- `node --check` on touched JS files
- `python3 -m py_compile` on touched Python files
- `git diff --check`

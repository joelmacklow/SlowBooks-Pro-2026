# Spec: System Account Decoupling

## Scope
Implement a settings-backed role resolution layer for runtime-selected system accounts.

## Required roles
- accounts receivable
- accounts payable
- GST control
- undeposited funds
- default sales income
- default expense
- wages expense
- employer KiwiSaver expense
- PAYE payable
- KiwiSaver payable
- ESCT payable
- child support payable
- payroll clearing

## Rules
- Runtime resolution order: explicit settings mapping -> legacy fallback -> existing auto-create behavior where already expected.
- Existing databases must keep working without immediate manual mapping.
- This slice does not replace the default chart seed.

## Validation
- Core posting/payment/payroll flows no longer depend directly on fixed account numbers.
- Frontend default bank/deposit selection no longer relies on a fixed account-number allowlist.

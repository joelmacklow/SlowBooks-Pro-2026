# Security Review — System Account Decoupling (2026-04-14)

## Scope
Reviewed the system-account decoupling slice changes in:
- `app/services/accounting.py`
- `app/routes/bills.py`
- `app/routes/bill_payments.py`
- `app/static/js/payments.js`
- `app/models/settings.py`

## Checks performed
- Verified runtime account resolution now prefers explicit settings-backed mappings and falls back to legacy discovery for compatibility.
- Reviewed posting/default-selection paths changed by the slice for broken-account-resolution risk.
- Re-ran full repo tests, JS checks, `py_compile`, and `git diff --check`.

## Findings
### CRITICAL
- None found.

### HIGH
- None found.

### MEDIUM
1. **Explicit account-role mappings are settings-backed but not yet exposed through a dedicated admin workflow**
   - The mapping contract now exists, but operational correctness still depends on either fallback behavior or setting those values through generic settings pathways.
2. **Legacy fallback remains intentionally permissive for compatibility**
   - This is appropriate for the transition slice, but the later chart-replacement/import work should reduce reliance on fixed-number fallback over time.

### LOW
1. **Frontend account selection now uses broader asset-account filtering**
   - This removes the fixed-number dependency, but it can expose more candidate deposit accounts than the old narrow list.

## Positive controls
- Explicit mapping now overrides legacy number assumptions for runtime account selection.
- Existing databases keep working through fallback behavior.
- No new shell execution, external calls, or unsafe file handling were introduced.
- Core posting tests and role-resolution integration tests passed after the decoupling change.

## Overall assessment
- **No CRITICAL/HIGH regressions found for this slice.**
- **Residual risk is MEDIUM** until the later chart replacement and admin configuration improvements reduce dependence on legacy fallback behavior.

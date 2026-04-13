# Security Review — NZ Chart Seed (2026-04-14)

## Scope
Reviewed the NZ chart-seed slice changes in:
- `app/seed/chart_of_accounts.py`
- `scripts/seed_database.py`
- `app/services/iif_export.py`
- README/docs updates tied to the new default chart

## Checks performed
- Verified the new default chart still contains the required GST/payroll/system accounts used by current posting flows.
- Verified seed/bootstrap now populates explicit system-account role settings for fresh databases.
- Re-ran full repo tests, JS checks, `py_compile`, and `git diff --check`.
- Added an IIF account-type compatibility check for the new NZ chart numbering.

## Findings
### CRITICAL
- None found.

### HIGH
- None found.

### MEDIUM
1. **The IRS/Henry Brown demo dataset is still mismatched with the new NZ default chart**
   - This slice intentionally leaves that data set alone.
   - The follow-up demo/mock-data slice should update those assumptions before presenting seeded demo data as NZ-native.

### LOW
1. **A few seeded accounts are adapted rather than direct one-to-one platform imports**
   - The default chart is Xero-derived plus explicit custom accounts needed by current runtime roles.
   - This is expected for the branch’s current accounting model.

## Positive controls
- Fresh seeded DBs no longer depend on one hardcoded numbering scheme for core runtime account selection.
- Existing GST/payroll posting tests remain green.
- IIF export classification for core NZ bank/AR/AP accounts remains valid after the chart swap.
- No new shell execution, external network calls, or unsafe file handling were introduced.

## Overall assessment
- **No CRITICAL/HIGH regressions found for this slice.**
- **Residual risk is MEDIUM** until the later NZ demo/mock-data slice removes the remaining IRS/US-oriented sample-data assumptions.

# Security Review — NZ PAYE Core + Posting (2026-04-14)

## Scope
Reviewed the PAYE core slice changes in:
- `app/routes/payroll.py`
- `app/services/nz_payroll.py`
- `app/models/payroll.py`
- `app/schemas/payroll.py`
- `app/services/accounting.py`
- `app/static/js/payroll.js`
- `app/static/js/employees.js`
- `alembic/versions/e5f6a7b8c9d0_implement_nz_paye_pay_runs.py`

## Checks performed
- Reviewed route/service/model/schema changes for injection, unsafe file/command use, and privilege-boundary issues.
- Confirmed payroll calculations and posting use local Decimal/ORM logic only; no dynamic SQL or shell execution added.
- Re-ran full repo tests, JS checks, `py_compile`, and `git diff --check`.
- Re-checked that user-facing HTML rendering in the new payroll UI escapes interpolated data.

## Findings
### CRITICAL
- None found.

### HIGH
- None found.

### MEDIUM
1. **Payroll PII is still exposed through the repo's broader no-auth/local-trust model**
   - Employee/payroll endpoints now expose and process IRD/tax/deduction data.
   - This slice did not add authentication/authorization, so the previously identified privacy risk remains and now covers active pay-run data too.

### LOW
1. **Rule-version coverage is intentionally narrow**
   - The slice implements versioned 2026 and 2027 rules for the supported pay-date range, but later tax years still require explicit rule updates.
2. **Child support modeling is still simplified**
   - The slice captures a per-pay amount and protected-net cap, but more complex notice/variation workflows remain future work.

## Positive controls
- New payroll routes validate employee activity and supported NZ payroll/tax-code inputs.
- Payroll processing rejects double-processing.
- Journal posting stays balanced and uses explicit system accounts.
- The new payroll UI uses escaped values for employee/run data.
- No secrets, arbitrary file paths, or new command execution paths were introduced.

## Overall assessment
- **No CRITICAL/HIGH security regressions identified in this slice.**
- **Residual risk remains MEDIUM** because payroll data still lives behind a trusted-local/private deployment model rather than an auth/privacy boundary.

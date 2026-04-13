# Security Review — NZ New/Departing Employee Filing (2026-04-14)

## Scope
Reviewed the employee filing slice changes in:
- `app/services/employee_filing.py`
- `app/routes/employees.py`
- `app/static/js/employees.js`

## Checks performed
- Verified starter/leaver exports are derived only from the selected employee and current settings.
- Reviewed use of existing employee dates as the source of truth and ensured no new command/path execution was introduced.
- Re-ran backend/frontend tests plus full repo verification.

## Findings
### CRITICAL
- None found.

### HIGH
- None found.

### MEDIUM
1. **Filing lifecycle is still not tracked separately from employee data**
   - Starter/leaver exports now exist, but the app still does not track whether those filings were already generated or submitted.
   - This is acceptable for the first single-user/local slice, but becomes important once RBAC/multiuser work begins.

### LOW
1. **Current employee dates remain mutable source-of-truth for filing output**
   - Editing start/end dates after export can change later generated output because there is no filing audit snapshot yet.

## Positive controls
- Starter export requires `start_date`.
- Leaver export requires `end_date`.
- Employee IRD number and employer IRD number are required.
- No new shell execution, arbitrary file paths, or external submission integrations were added.

## Overall assessment
- **No CRITICAL/HIGH regressions found for this slice.**
- **Residual risk remains MEDIUM** until a later RBAC-linked filing-status/audit model exists.

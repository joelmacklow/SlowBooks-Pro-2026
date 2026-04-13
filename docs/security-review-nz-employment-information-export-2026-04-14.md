# Security Review — NZ Employment Information Export (2026-04-14)

## Scope
Reviewed the Employment Information export slice changes in:
- `app/services/payday_filing.py`
- `app/routes/payroll.py`
- `app/static/js/payroll.js`
- `app/models/settings.py`
- `app/static/js/settings.js`

## Checks performed
- Verified export generation is restricted to processed pay runs only.
- Verified export content is scoped to the selected run only.
- Reviewed file generation, settings fallbacks, and UI export actions for unsafe interpolation or path/command risks.
- Re-ran targeted backend/UI tests and will be included in full repo verification before completion.

## Findings
### CRITICAL
- None found.

### HIGH
- None found.

### MEDIUM
1. **Payroll data exposure risk remains unchanged at the app level**
   - Employment Information export adds another externally downloadable payroll artifact.
   - The slice does not add RBAC/auth/privacy controls, so the existing trusted-local/private deployment assumption remains the main residual risk.

### LOW
1. **Employee-details filing remains deferred**
   - This slice only exports Employment Information for processed pay runs.
   - New/departing employee filing is intentionally left for a later slice.

## Positive controls
- Draft runs cannot be exported.
- Export validation requires core employer/contact filing inputs.
- Export content is generated from one processed run only.
- No new shell execution, remote calls, or arbitrary file-path handling were introduced.

## Overall assessment
- **No CRITICAL/HIGH regressions found for this slice.**
- **Residual risk remains MEDIUM** because payroll exports still live behind the repo's broader no-auth/local-trust model.

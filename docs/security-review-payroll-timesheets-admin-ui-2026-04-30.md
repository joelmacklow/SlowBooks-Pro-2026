# Security review: payroll timesheets admin UI surfacing (Bugfix)

## Date
2026-04-30

## Scope reviewed
- `app/static/js/payroll.js`
- `tests/js_payroll_timesheet_review_ui.test.js`
- existing payroll UI regression tests touched by the same UI file

## Threat-focused checks
1. **Permission gating**
   - The new Timesheet Review panel is only rendered when the current user has one of the explicit timesheet admin permissions.
   - The panel does not appear for payroll users who lack timesheet permissions.
   - Review actions are only wired into the payroll page, not global navigation.

2. **Endpoint exposure**
   - The UI surfaces the existing admin endpoints for:
     - period readiness
     - pay-run readiness
     - detail
     - audit
     - correction
     - approve/reject
     - bulk approve
     - export
   - Endpoints remain server-enforced; the UI does not broaden access on its own.

3. **Sensitive data handling**
   - The review panel shows payroll/timesheet data only after authenticated API calls.
   - The export button uses the server-side CSV endpoint and does not inline raw data into the DOM.
   - The UI does not log or persist payroll PII.

4. **Injection and UI safety**
   - Rendered values are escaped before being inserted into the modal/panel HTML.
   - The rejection reason and correction reason are submitted as form payloads, not interpolated into executable script.
   - No new shell execution, file writes, or outbound network calls were introduced.

## Findings
- **No CRITICAL/HIGH issues identified in this bugfix.**
- Residual risk remains **MEDIUM** because the payroll page still depends on client-side permission checks for discoverability; the server remains the enforcement point, but the screen is still a sensitive admin surface.

## Verification evidence
- `node --check app/static/js/payroll.js`
- `node tests/js_payroll_timesheet_review_ui.test.js`
- `node tests/js_nz_payroll_ui.test.js`
- `node tests/js_payroll_filing_audit_ui.test.js`
- `git diff --check`


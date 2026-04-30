# Plan — Timesheet start/end entry UI bugfix

## Objective
Fix the payroll timesheet review correction error caused by brittle time value handling and update the employee self-service timesheet UI so employees can enter start/end/break times with calculated daily hours instead of entering hours directly.

## Constraints
- Keep the fix frontend-focused.
- Preserve the existing payroll timesheet APIs and server-side validation.
- Keep the timesheet review/admin workflow available from the payroll page.
- Do not widen permissions or expose payroll data outside the existing gates.

## Implementation sketch
1. Harden payroll review time field rendering so correction forms safely format string/date-like time values.
2. Update the employee self-service timesheet editor to support:
   - start time,
   - end time,
   - break minutes,
   - calculated total hours,
   - without requiring manual total-hour entry for start/end mode.
3. Keep duration-mode compatibility if needed for existing records, but render computed hours read-only in the UI.
4. Add targeted JS tests for both the review correction form and the employee self-service editor.

## Impacted files
- `app/static/js/payroll.js`
- `app/static/js/timesheets_self_service.js`
- `tests/js_payroll_timesheet_review_ui.test.js`
- `tests/js_timesheets_self_service_submit.test.js` or a new dedicated self-service entry-mode test

## Test plan
- Add or update JS tests first.
- Run `node --check` on the touched frontend files.
- Run the targeted JS tests.
- Run `git diff --check`.

## Risk notes
- The UI must continue to submit a backend-compatible payload for both duration and start/end entries.
- Any calculated-hours display should remain advisory/read-only and not replace server-side validation.

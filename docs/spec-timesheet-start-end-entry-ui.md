# Test Spec — Timesheet start/end entry UI bugfix

## Slice goal
Prove the payroll review correction UI no longer crashes on time values and the employee self-service timesheet UI supports start/end/break entry with calculated hours.

## Required behavior
- Payroll review correction rows render start/end inputs without a `slice` error.
- Employee timesheet entry supports start/end/break input fields.
- Daily hours are calculated from the entered times instead of being manually entered in start/end mode.
- Existing submit/update workflows still post valid payloads to the same endpoints.

## Tests to add
1. `test_timesheet_review_correction_time_inputs_handle_string_or_null_values`
2. `test_employee_timesheet_editor_supports_start_end_break_entry`
3. `test_employee_timesheet_editor_computes_daily_hours_from_start_end_times`

## Verification
- Run the targeted JS test files.
- Run `node --check` on the touched frontend files.
- Run `git diff --check`.

## Non-goals
- No backend route or schema changes.
- No new permissions or navigation changes.
- No payroll import/integration work.

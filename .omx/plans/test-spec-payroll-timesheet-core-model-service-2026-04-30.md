# Test Spec: Payroll timesheet core model/service slice

## Purpose
Prove the Slice 2 timesheet model and service lifecycle are safe, deterministic, and ready for later employee/admin routes without exposing payroll PII or modifying pay-run behavior.

## Target files
- New `tests/test_timesheets_service.py`.
- New `app/models/timesheets.py`.
- New `app/schemas/timesheets.py`.
- New `app/services/timesheets.py`.
- `app/models/__init__.py`.
- Alembic migration under `alembic/versions/`.

## Test setup
- Use in-memory SQLite with `Base.metadata.create_all()` like existing payroll tests in `tests/test_nz_payroll_data_model.py:14-20` and `tests/test_nz_payroll_runs.py:16-24`.
- Register `Employee`, `PayRun`, `PayStub`, `Timesheet`, `TimesheetLine`, and `TimesheetAuditEvent` before metadata creation.
- Create employees through existing payroll model/route helpers when practical so the tests stay compatible with current `Employee` fields from `app/models/payroll.py:30-63`.

## Required tests
1. `test_create_draft_timesheet_with_duration_lines_calculates_total`
   - Create an hourly employee.
   - Create a draft period with two duration lines.
   - Assert status is `draft`, total is the sum rounded to `0.01`, lines persist, and a create audit event exists.

2. `test_create_draft_timesheet_with_start_end_break_calculates_total`
   - Create a same-day line with start/end times and break minutes.
   - Assert net hours are calculated correctly and rounded to `0.01`.

3. `test_duplicate_employee_period_is_rejected`
   - Create one draft for employee/period.
   - Attempt another timesheet for the same employee/period.
   - Assert a service-level error before/at commit and only one timesheet remains.

4. `test_invalid_period_and_out_of_period_work_date_are_rejected`
   - Reject `period_start > period_end`.
   - Reject a line where `work_date` is outside the period.

5. `test_invalid_duration_values_are_rejected`
   - Reject negative duration.
   - Reject zero duration.
   - Reject duration above 24 hours for a single line.

6. `test_invalid_start_end_values_are_rejected`
   - Reject missing start/end for `start_end` mode.
   - Reject same-time or negative net hours.
   - Reject break minutes greater than/equal to the shift span.
   - Reject overnight shifts explicitly for MVP.

7. `test_update_draft_replaces_lines_recalculates_total_and_audits`
   - Update a draft timesheet with new lines.
   - Assert old lines are replaced safely, total is recalculated, and an update audit event exists.

8. `test_submitted_approved_and_locked_timesheets_cannot_be_edited`
   - Submit a draft.
   - Assert update fails while submitted.
   - Approve then lock.
   - Assert update fails in approved and locked states.

9. `test_lifecycle_transitions_require_valid_source_state`
   - Assert draft/rejected can submit.
   - Assert only submitted can approve/reject.
   - Assert only approved can lock.
   - Assert repeated submit/approve/reject/lock operations fail clearly.

10. `test_reject_requires_reason_and_records_reason_in_audit`
    - Submit a draft.
    - Reject without reason and assert failure.
    - Reject with reason and assert status, reason, and audit event.

11. `test_rejected_timesheet_can_be_corrected_and_resubmitted`
    - Reject a submitted timesheet.
    - Update rejected lines.
    - Assert status returns to draft.
    - Resubmit and assert audit trail records correction and submit.

12. `test_lock_records_actor_and_prevents_later_mutation`
    - Approve a submitted timesheet.
    - Lock it with an actor id.
    - Assert locked timestamp/status/audit event and subsequent update/reject/approve fail.

13. `test_response_schema_excludes_employee_payroll_private_fields`
    - Serialize a timesheet detail/list response.
    - Assert `ird_number`, `pay_rate`, `tax_code`, KiwiSaver, student loan, and child-support fields are absent.

14. `test_audit_events_are_written_for_each_mutation_in_order`
    - Create, update, submit, approve, lock.
    - Assert ordered audit actions and status transitions.

15. `test_payroll_run_behavior_unchanged_by_timesheet_models`
    - Run or preserve existing payroll regression coverage proving manual hourly `PayStub.hours` still works.

## Verification commands
- `python -m pytest tests/test_timesheets_service.py`
- `python -m pytest tests/test_nz_payroll_data_model.py tests/test_nz_payroll_runs.py`
- `python -m compileall app/models app/schemas app/services tests`
- `git diff --check`

## Security review assertions
- No route or router registration is added in this slice.
- No schema serializes full `Employee` objects.
- Audit metadata does not store payroll-private fields unless a later compliance decision explicitly requires it.
- Actor ids are recorded for audit but are not trusted as authorization decisions in this service-only slice.
- Database constraints enforce duplicate prevention even if a caller bypasses the service.

## Out of scope tests
- Self-service route access control and IDOR tests.
- Admin approval route permission tests.
- CSV/print export tests.
- Payroll pay-run import and locking-through-pay-run tests.
- Frontend rendering tests.

# Plan — Payroll timesheets admin review API

## Objective
Deliver slice 4 of the payroll timesheets feature: an admin review API that lets payroll staff inspect readiness by period or pay run, view submitted timesheets, correct them with an audit reason, approve/reject/bulk-approve, and export scoped CSV data.

## Constraints
- Keep the change backend-focused; no UI slice work yet.
- Reuse the existing timesheet model/service layer rather than growing payroll routes.
- Preserve employee self-service boundaries and require explicit admin permissions for review actions.
- Treat payroll/timesheet data as sensitive: export filenames, filters, and responses must stay scoped and deterministic.

## Implementation sketch
1. Add admin-focused timesheet permissions to the auth role matrix.
2. Extend the timesheet schema/service layer with:
   - readiness list/grouping helpers for a period or pay run,
   - admin correction that keeps a submitted timesheet submitted while recording an audit reason,
   - bulk approval for submitted timesheets,
   - audit listing,
   - admin CSV export helpers.
3. Add admin routes under `app/routes/timesheets.py` for:
   - period readiness,
   - pay-run readiness,
   - detail,
   - correction,
   - approve/reject/bulk approve,
   - audit history,
   - CSV export.
4. Add targeted route tests covering positive admin paths and negative RBAC/ownership boundaries.

## Impacted files
- `app/services/auth.py`
- `app/schemas/timesheets.py`
- `app/services/timesheets.py`
- `app/routes/timesheets.py`
- `tests/test_timesheets_admin_routes.py`
- `tests/test_admin_rbac_protection.py` if permission regression coverage needs to expand

## Test plan
- Add targeted admin route tests first.
- Verify admin list/detail/correct/approve/reject/bulk approve/audit/export behavior.
- Verify payroll viewer or other non-admin roles cannot approve or export.
- Run the targeted tests, then `git diff --check`.

## Risk notes
- Correcting a submitted timesheet is sensitive because it mutates payroll source data; keep the audit trail explicit and avoid changing status accidentally.
- CSV export must not leak unrelated employee/payroll fields or accept unbounded filters.
- Bulk approve should fail safely on missing or non-submitted records.

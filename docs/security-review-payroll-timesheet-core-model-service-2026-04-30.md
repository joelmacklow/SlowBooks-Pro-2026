# Security review: payroll timesheet core model/service (Slice 2)

Date: 2026-04-30  
Scope:
- `app/models/timesheets.py`
- `app/services/timesheets.py`
- `app/schemas/timesheets.py`
- `alembic/versions/y2z3a4b5c6d7_add_timesheet_core_tables.py`
- `tests/test_timesheets_service.py`

## Checks performed

1. **Auth/routing boundary**
   - Confirmed this slice adds no routes and no router registration.
   - No new permissions were introduced.

2. **PII exposure boundary**
   - Timesheet response schemas are scoped to timesheet fields and IDs only.
   - Employee payroll-private fields (`ird_number`, tax/deduction settings, pay rate) are not serialized by timesheet schemas.
   - Added regression test coverage for this boundary.

3. **Tamper resistance**
   - Service enforces lifecycle state transitions:
     - draft/rejected -> submitted
     - submitted -> approved/rejected
     - approved -> locked
   - Mutation of submitted/approved/locked timesheets is blocked.
   - Duplicate employee-period timesheets are blocked at both service and database constraint layers.

4. **Audit integrity**
   - Create/update/submit/approve/reject/lock paths write a `timesheet_audit_events` record with actor ID and status transition context.
   - Rejection requires a non-empty reason and persists it in the audit trail.

5. **Injection / shell / filesystem / SSRF / deserialization**
   - No shell execution, file IO, dynamic code execution, outbound HTTP, or deserialization surface added in this slice.
   - No new dependencies introduced.

## Findings

- **No CRITICAL/HIGH issues identified in this slice.**
- Residual risk remains **MEDIUM** at product level because route-level auth/IDOR protections are deferred to later timesheet route slices.

## Follow-up recommendations

1. Enforce `resolve_employee_link` and strict RBAC checks when self-service/admin timesheet routes are introduced.
2. Add immutable linkage/locking rules when timesheets are tied to processed pay runs in the later payroll-integration slice.

# Spec: NZ New/Departing Employee Filing

## Scope
Implement starter/leaver filing from existing employee records only.

## Output
- Add employee filing export routes under `/api/employees/{emp_id}/filing/...`
- Provide separate starter and leaver exports based on `start_date` / `end_date`
- Use downloadable CSV output and NZ payday-filing terminology

## Rules
- Starter export requires `start_date`
- Leaver export requires `end_date`
- Employee IRD number and core identity fields are required
- No filing-status/audit tracking model in this slice
- Add a tracked later todo for RBAC-linked filing-status/audit support

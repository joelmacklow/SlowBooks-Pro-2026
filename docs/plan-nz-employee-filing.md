# NZ New/Departing Employee Filing Slice

## Summary
Add the first employee-details filing slice using existing employee dates/data as the source of truth. Generate starter/leaver filing output without introducing a separate filing-status/audit model yet.

## Key Changes
- Add employee filing export for starter/leaver cases derived from `start_date` and `end_date`.
- Reuse current employee/setup/settings data and shared payday-filing helpers where possible.
- Expose filing actions in the employee UI only when starter/leaver conditions are met.
- Record a later RBAC-linked todo for a dedicated filing-status/audit model.

## Test Plan
- Backend tests for starter export, leaver export, and required-field validation.
- Frontend test for employee filing action visibility.
- Full repo verification plus explicit payroll/file-export security review.

## Defaults
- No filing tracker yet; current employee dates are the source of truth.

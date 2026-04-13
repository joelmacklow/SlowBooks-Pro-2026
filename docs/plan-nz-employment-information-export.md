# NZ Employment Information Export Slice

## Summary
Add a per-processed-pay-run IRD Employment Information export file using the current payroll run/stub/company data model and the current IRD file-upload specification.

## Key Changes
- Add a processed-run-only export route for one payroll run.
- Generate an IRD Employment Information CSV file with HEI2 header and DEI employee lines.
- Add any minimum missing settings fields required for the file header and validate them before export.
- Expose the export action from the Payroll UI for processed runs only.
- Record new/departing employee filing as a separate later todo.

## Test Plan
- Backend tests for processed export success, draft rejection, required-field validation, and file content/filename.
- Frontend tests for export action visibility on processed runs only.
- Full repo verification and explicit payroll/file-export security review.

## Defaults
- One processed pay run equals one export file.
- IRD submission is out of scope; this slice only generates the upload file.
- Employee-details filing remains deferred.

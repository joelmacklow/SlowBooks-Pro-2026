# Report FY Period Options Bugfix Specification

## Goal
Make financial report period selectors support financial-year choices in addition to the current calendar-based options.

## Required Behavior
- Report period dropdowns must include `This FY` and `Last FY`.
- FY date ranges must be derived from the configured `financial_year_start` setting when available.
- If no FY setting is available, FY options should safely behave like calendar-year ranges rather than failing.
- Existing calendar options and custom date handling must continue to work unchanged.

## Constraints
- Do not add new permissions requirements for reading the FY boundary.
- Do not change report API contracts beyond the dates already sent by the frontend.
- Do not remove existing calendar period options.

## Verification
- Targeted JS regression coverage for FY option rendering and date-range calculation.
- Targeted Python regression confirming public settings expose `financial_year_start`.
- `node --check app/static/js/reports.js`
- `git diff --check`

# Report FY Period Options Bugfix Plan

## Objective
Add financial-year period choices to the financial report date selector so users can pick This FY and Last FY in addition to the existing calendar periods.

## Constraints
- Keep the existing report modal flow and custom-date behavior intact.
- Reuse the current public settings path for financial-year configuration rather than adding a new permissions requirement.
- No new dependencies or report route redesign.

## Implementation Sketch
- Expose the financial-year start setting through the public settings payload consumed by the app.
- Extend the reports period selector with This FY and Last FY options.
- Compute FY date ranges from the configured financial-year start, falling back safely to calendar year if the setting is unavailable.
- Add focused JS coverage for the new period options/ranges and a backend regression to confirm public settings expose the FY start value.

## Impacted Files
- `app/routes/settings.py`
- `app/static/js/reports.js`
- `tests/js_reports_period_options.test.js`
- `tests/test_settings_localization.py`

## Test Plan
- Add/update targeted tests for public settings and report period calculations.
- Run the new JS test plus relevant existing JS syntax checks.
- Run targeted Python settings tests and `git diff --check`.

## Risk Notes
- Incorrect FY boundary math can shift report periods by a year around the FY rollover.
- If the public settings payload omits the FY start, the selector would silently fall back to calendar year and mask the bug.

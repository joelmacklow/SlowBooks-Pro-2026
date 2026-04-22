# Balance Sheet Current Earnings Bugfix Plan

## Objective
Fix the balance sheet so it reflects unclosed earnings in equity and explicitly shows whether Assets equals Liabilities plus Equity.

## Constraints
- Keep the existing balance-sheet route and modal flow intact.
- Limit the slice to reporting/presentation logic; do not introduce a year-end closing workflow.
- No new dependencies or account-model changes.

## Implementation Sketch
- Update balance-sheet calculation to include earnings-to-date from income, COGS, and expense accounts in the reported equity total.
- Expose balance-check fields (`Total Liabilities + Equity`, `Difference`, balanced flag) from the API response.
- Render the earnings row and balance-check rows in the UI/PDF.
- Add targeted regression coverage for balancing behavior and rendered balance-sheet output.

## Impacted Files
- `app/routes/reports.py`
- `app/static/js/reports.js`
- `tests/test_report_signs.py`
- `tests/test_xero_import.py`
- `tests/js_reports_balance_sheet_content.test.js`

## Test Plan
- Add/update backend tests for current-earnings inclusion and zero-difference balancing.
- Add/update frontend rendering coverage for the new balance-sheet rows.
- Run targeted JS and Python report tests plus `git diff --check`.

## Risk Notes
- Labeling earnings incorrectly could confuse users if a future closing process is added later.
- If the balance check uses inconsistent sign treatment, the report could still appear out of balance even after the equity fix.

# Test Spec — Dashboard FY profit and invoice list overdue follow-up

## Date
2026-04-21

## Red/Green plan
- Add/extend backend tests first for dashboard financial-year boundaries.
- Add/extend invoice list JS tests first for sorting, overdue filtering, overdue-day rendering, and reminder column output.
- Implement the smallest route/schema/UI changes needed to satisfy those tests.
- Re-run targeted checks and safety verification.

## Verification targets
- `tests/test_dashboard_snapshot_metrics.py`
  - current FY period uses company settings
  - profit totals respect the FY window
- new/updated invoice JS tests
  - overdue filter
  - sort toggles by column
  - overdue days text
  - reminder summary rendering
  - red overdue due date styling/class

## Safety checks
- `node` targeted invoice/dashboard JS tests
- targeted Python unittest for dashboard metrics
- `node --check app/static/js/invoices.js`
- `python3 -m py_compile ...`
- `git diff --check`

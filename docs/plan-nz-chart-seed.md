# NZ Chart Seed Slice

## Summary
Replace the default chart seed with an NZ-oriented chart derived from the provided Xero-style chart source, and populate system-account role settings during seeding so fresh databases do not rely on legacy fallback.

## Key Changes
- Replace the default chart in `app/seed/chart_of_accounts.py`.
- Update `scripts/seed_database.py` to assign system-account role settings after seeding.
- Keep required GST/payroll/system accounts present and correctly mapped.
- Update docs that still describe the old QB contractor chart as the branch default.
- Leave IRS/Henry Brown demo data for a later slice.

## Test Plan
- Add/adjust chart-seed and role-population tests.
- Run full repo verification and explicit accounting/seed safety review.

## Defaults
- Source chart for this slice is `/home/joelmacklow/Downloads/ChartOfAccounts.csv`.

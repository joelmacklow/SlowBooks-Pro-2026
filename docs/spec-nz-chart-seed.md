# Spec: NZ Chart Seed

## Scope
Implement the NZ default chart for new database/seed flows using the provided Xero-style chart as the reference source.

## Rules
- `app/seed/chart_of_accounts.py` becomes the canonical NZ default chart.
- Seed/bootstrap must also populate system-account role mappings for the current runtime roles.
- Required GST/payroll/system accounts used by the app must remain present.
- This slice does not change the IRS/Henry Brown demo/mock dataset.

## Validation
- Seeded chart includes core NZ bank, revenue, COGS, expense, GST, receivable/payable, and payroll accounts.
- Fresh seeded DBs get explicit system-account role settings.
- Existing GST/payroll posting tests remain green.

# Spec: NZ Employment Information Export

## Source of truth
- IRD Payday Filing File Upload Specification 2026
- Scope limited to Employment Information CSV export for one processed pay run

## Output
- Route: `GET /api/payroll/{run_id}/employment-information/export`
- Response: downloadable `text/csv`
- Filename: `EmploymentInformation_<paydate>_run-<id>.csv`
- Content structure:
  - 1 `HEI2` header line
  - 1+ `DEI` employee lines

## Header mapping
- Record indicator: `HEI2`
- Employer IRD number: `settings.ird_number` (required)
- Paydate: `pay_run.pay_date` as `YYYYMMDD`
- Final return for employer: `N`
- Nil return indicator: `N`
- PAYE intermediary IRD number: blank
- Payroll contact name: `settings.payroll_contact_name`, fallback `settings.company_name`
- Payroll contact work phone: `settings.payroll_contact_phone`, fallback `settings.company_phone`
- Payroll contact email: `settings.payroll_contact_email`, fallback `settings.company_email`
- Total employee lines: count of stubs in run
- Total gross earnings: sum of stub gross pay
- Total prior period gross adjustments: `0.00`
- Total earnings not liable for ACC: `0.00`
- Total PAYE/tax: sum of stub PAYE
- Total prior period PAYE adjustment: `0.00`
- Total child support deductions: sum of stub child support deduction
- Total student loan deductions: sum of stub student loan deduction
- Total SLCIR deductions: `0.00`
- Total SLBOR deductions: `0.00`
- Total KiwiSaver deductions: sum of stub KiwiSaver employee deduction
- Total net KiwiSaver employer contributions: sum of `(employer_kiwisaver_contribution - esct)`
- Total ESCT deducted: sum of stub ESCT
- Total amounts deducted: sum of PAYE + child support + student loan + KiwiSaver employee + net employer KiwiSaver + ESCT
- Total tax credits for payroll donations: `0.00`
- Total family tax credits: `0.00`
- Total employee share scheme: `0.00`
- Payroll package/version identifier: constant `SlowBooksNZ_nz-localization_v1`
- IR form version number: `0001`

## Detail mapping
- Record indicator: `DEI`
- Employee IRD number: employee `ird_number`, else `000000000`
- Employee name: `first_name + last_name`
- Employee tax code: stub tax code
- Employment start date: include only if inside pay period, else blank
- Employment finish date: include only if inside pay period, else blank
- Employee pay period start/end: run period start/end as `YYYYMMDD`
- Employee pay cycle mapping:
  - weekly -> `WK`
  - fortnightly -> `FT`
  - monthly -> `MT`
- Hours paid: stub hours in centesimal form, default `0`
- Gross earnings and/or schedular payments: stub gross pay
- Prior period gross adjustments: `0.00`
- Earnings not liable for ACC earners’ levy: `0.00`
- Lump sum indicator: `0`
- PAYE/tax: stub PAYE
- Prior period PAYE adjustment: `0.00`
- Child support deductions: stub child support deduction
- Child support code: blank
- Student loan deductions: stub student loan deduction
- SLCIR deductions: `0.00`
- SLBOR deductions: `0.00`
- KiwiSaver deductions: stub KiwiSaver employee deduction
- Net KiwiSaver employer contributions: `employer_kiwisaver_contribution - esct`
- ESCT deducted: stub ESCT
- Tax credits for payroll donations: `0.00`
- Family tax credits: `0.00`
- Employee share scheme: `0.00`

## Validation
- Run must exist.
- Run must be `processed`.
- `settings.ird_number` is required.
- Contact phone and contact email are required after fallback resolution.
- Only currently supported pay frequencies (`weekly`, `fortnightly`, `monthly`) may be exported.
- Export uses only stubs belonging to the selected run.

## Deferred
- New/departing employee filing
- EI amendments
- Multi-run batch export
- myIR submission

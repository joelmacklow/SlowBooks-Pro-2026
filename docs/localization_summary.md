# New Zealand Localization Summary

This document captures the current localization audit for turning SlowBooks Pro 2026 into a New Zealand-localized version.

The GitHub branch `nz-localization` exists remotely, based on `main` at commit `6fadfa755c9b1625abc5f639c12a6d9edcfb9c78`. At the time of the audit, the local checkout was still on `main`, so local work should begin with:

```bash
git fetch origin nz-localization
git switch nz-localization
```

## Assessment

The app is strongly US-shaped in tax, payroll, addresses, reports, PDF/UI copy, seed data, and import/export behavior. The broad direction from the external review is accurate, but the code audit found several additional surfaces that need attention:

- Purchase-side GST is more than a label change. Bills already debit account `2200` for tax, so the current single "Sales Tax Payable" account is being used as both collected-output tax and purchase-input tax.
- Import/export paths are a major localization surface. CSV and IIF logic use State/ZIP conventions, QuickBooks-style address parsing, and "Sales Tax Payable" labels.
- GST calculation is duplicated across invoices, bills, credit memos, purchase orders, estimates, and recurring invoices.
- Document updates recalculate totals but do not consistently rebuild/reverse journal entries, which becomes riskier once GST posting rules are introduced.
- There is no `tests/` directory, so GST and payroll changes should start with focused regression tests.
- Schema changes need Alembic migrations under `alembic/versions`.

## Official NZ Anchors

Use official Inland Revenue and ACC material when implementing the localized behavior:

- Inland Revenue GST overview: <https://www.ird.govt.nz/gst>
- Inland Revenue charging GST: <https://www.ird.govt.nz/gst/charging-gst>
- Inland Revenue claiming GST: <https://www.ird.govt.nz/en/gst/claiming-gst>
- Inland Revenue payday filing paper information: <https://www.ird.govt.nz/employing-staff/payday-filing/filing-employment-information-by-paper>
- Inland Revenue PAYE file upload specification 2026: <https://www.ird.govt.nz/-/media/project/ir/home/documents/digital-service-providers/payday-filing-file-upload-specification-2026.pdf?modified=20250804033830>
- Inland Revenue KiwiSaver employee deduction rates: <https://www.ird.govt.nz/kiwisaver/kiwisaver-for-employers/contributions-and-deductions/update-employee-deduction-rate-for-kiwisaver>
- Inland Revenue KiwiSaver employer contributions: <https://www.ird.govt.nz/kiwisaver/kiwisaver-for-employers/contributions-and-deductions/employer-contributions-to-kiwisaver-and-complying-funds>
- Inland Revenue ACC levy rates: <https://www.ird.govt.nz/acclevy>

Key design facts from those sources:

- GST is charged at `15%`.
- For GST-inclusive prices, the GST component is calculated as `3/23` of the GST-inclusive price.
- GST payable/refundable is based on output tax less input tax.
- Payroll should align with current payday filing / Employment Information processes, not legacy US-style withholding.
- PAYE tax codes include codes such as `M`, `ME`, `S`, `SH`, `ST`, `SA`, and `SL` variants.
- KiwiSaver employee contribution rates are listed as `3.5%`, `4%`, `6%`, `8%`, or `10%`, with employer contributions generally at least `3%`.
- ACC earners' levy is part of PAYE calculations for ordinary PAYE wages; the app should still version rates/caps carefully.

## Confirmed Code Gaps

### Settings

Settings are stored as key-value rows and the API only accepts keys listed in `DEFAULT_SETTINGS`.

Relevant files:

- `app/models/settings.py`
- `app/routes/settings.py`
- `app/static/js/settings.js`

NZ fields need to be added to defaults and surfaced in the UI/API together.

### Currency And Dates

Currency and date formatting are hardcoded for the US:

- `app/static/js/utils.js` uses `Intl.NumberFormat('en-US', { currency: 'USD' })`.
- `app/services/pdf_service.py` formats currency with `$` and dates with US-style month/day/year strings.

### GST Calculation

Tax is currently invoice-level rather than line-level. `Item.is_taxable` exists, but invoice total calculation ignores it.

Relevant files:

- `app/models/items.py`
- `app/models/invoices.py`
- `app/routes/invoices.py`
- `app/routes/estimates.py`
- `app/routes/bills.py`
- `app/routes/credit_memos.py`
- `app/routes/purchase_orders.py`
- `app/services/recurring_service.py`

### GST Posting

The app uses account `2200` as "Sales Tax Payable" for both sales tax collected and tax on bills.

Relevant files:

- `app/services/accounting.py`
- `app/routes/invoices.py`
- `app/routes/bills.py`
- `app/routes/credit_memos.py`
- `app/services/recurring_service.py`
- `app/seed/chart_of_accounts.py`

### Payroll

Payroll is US-specific in both storage and calculation:

- Employee uses `ssn_last_four`, filing status, allowances, state, and zip.
- Pay stubs store federal tax, state tax, Social Security, and Medicare.
- Payroll service hardcodes Social Security, Medicare, federal brackets, and a flat state tax.

Relevant files:

- `app/models/payroll.py`
- `app/schemas/payroll.py`
- `app/routes/payroll.py`
- `app/routes/employees.py`
- `app/services/payroll_service.py`
- `app/static/js/payroll.js`
- `app/static/js/employees.js`

### Addresses

Customer and vendor records default country to `US`; forms and templates still use State/ZIP labels.

Relevant files:

- `app/models/contacts.py`
- `app/schemas/contacts.py`
- `app/static/js/customers.js`
- `app/static/js/vendors.js`
- `app/static/js/settings.js`
- `app/templates/invoice_pdf.html`
- `app/templates/invoice_pdf_v2.html`
- `app/templates/estimate_pdf.html`
- `app/templates/statement_pdf.html`
- `app/templates/invoice_email.html`

### Tax Reporting

Schedule C is hardcoded in routes, model comments, service mappings, CSV headings, UI, and docs.

Relevant files:

- `app/models/tax.py`
- `app/routes/tax.py`
- `app/services/tax_export.py`
- `app/static/js/tax.js`
- `README.md`

### Import And Export

CSV and IIF import/export encode US address assumptions and sales-tax labels.

Relevant files:

- `app/services/csv_import.py`
- `app/services/csv_export.py`
- `app/services/iif_import.py`
- `app/services/iif_export.py`
- `app/static/js/iif.js`

## Consolidated Todo

1. Checkout the local branch:
   `git fetch origin nz-localization` then `git switch nz-localization`.

2. Add a localization foundation:
   Add settings for `country=NZ`, `tax_regime=NZ`, `currency=NZD`, `locale=en-NZ`, `timezone=Pacific/Auckland`, `ird_number`, `gst_number`, `gst_registered`, `gst_basis`, `gst_period`, and `prices_include_gst`.

3. Centralize formatting:
   Replace hardcoded `en-US`, `USD`, `$`, and US date strings with locale-aware frontend and PDF helpers.

4. Refactor address fields without breaking data:
   Prefer label/remap first (`Region`, `Postcode`, `Country=NZ`), then consider schema migrations later. Update settings, customers, vendors, employees, PDFs, CSV, and IIF.

5. Create a GST domain model:
   Add GST codes/rates such as `GST15`, `ZERO`, `EXEMPT`, and `NO_GST`. Consider `IMPORT` or `REVERSE_CHARGE` later if needed.

6. Store GST per line:
   Add GST code/rate to invoice lines, estimate lines, credit memo lines, bill lines, purchase order lines, and recurring invoice lines.

7. Build one GST calculation service:
   Support exclusive and inclusive pricing, `3/23` GST-inclusive extraction, rounding, taxable totals, zero-rated totals, exempt totals, output GST, and input GST.

8. Rework journal posting:
   Replace `get_sales_tax_account_id()` with GST-aware account helpers. Decide whether to use separate `GST Collected` and `GST Paid` accounts plus `GST Payable`, or one GST control account with reporting splits.

9. Fix posting lifecycle behavior:
   Ensure edits, voids, duplicates, and conversions either reverse/repost journal entries correctly or enforce immutable posted documents.

10. Replace the sales tax report with a GST return report:
    Include sales/output GST, purchases/input GST, net GST payable/refundable, GST period/basis, zero-rated/exempt supplies, and drilldowns to source transactions.

11. Replace Schedule C:
    Remove or hide Schedule C routes/UI for NZ mode. Replace later with NZ income tax outputs after deciding whether the target is IR3 business summary, IR10-style financial statements, or accountant export.

12. Rebuild payroll around NZ:
    Replace SSN/filing status/allowances with IRD number, tax code, KiwiSaver status/rate, student loan, child support, start/end dates, ESCT rate, pay frequency, and any required payday filing fields.

13. Implement PAYE using versioned official tables:
    Use IRD PAYE tables/specs by tax year instead of hardcoded constants. Model PAYE, student loan, KiwiSaver employee deduction, employer KiwiSaver, ESCT, child support, and payday filing fields.

14. Replace payroll outputs:
    Add NZ payslip labels and Employment Information / payday filing export. Avoid naming this "IRFile/EMS" until confirmed by current IRD requirements.

15. Seed NZ chart and demo data:
    Create NZ chart accounts for GST, PAYE, KiwiSaver, ESCT, wages, and any ACC-related expenses/liabilities as appropriate. Replace IRS Pub 583 seed/demo data with NZ examples.

16. Add Alembic migrations:
    Any model/schema changes need migrations under `alembic/versions`. Also ensure multi-company creation and seed flows use the NZ defaults and chart.

17. Update UI copy everywhere:
    Replace Sales Tax, Federal Tax, State Tax, SS, Medicare, EIN, ZIP, State, IRS, and Schedule C. Update README and screenshots/docs.

18. Add tests:
    Add focused tests for GST inclusive/exclusive math, line GST codes, document posting, credit memo reversals, bill input GST, PAYE examples, and formatting.

19. Decide multi-currency scope:
    For a pure NZ fork, start with single-currency `NZD` formatting. Full multi-currency is a separate accounting feature involving exchange rates, realized gains/losses, bank-account currencies, and reporting currency.

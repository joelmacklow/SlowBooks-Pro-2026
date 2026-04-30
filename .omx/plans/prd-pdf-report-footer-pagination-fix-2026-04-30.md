# PRD — Fix page numbering in multipage PDF report footers

## Date
2026-04-30

## Objective
Fix the page numbering bug in multipage PDF reports so each page shows its own page number instead of repeating the final page number.

## Problem
Current PDF report footers use fixed-position elements with CSS page counters. In multipage reports, the generated footer can repeat the final page number on every page, e.g. a 9-page general ledger report showing `Page 9 of 9` on all pages.

## Scope
### In scope
- `app/templates/report_pdf.html`
- PDF report footer pagination logic
- regression tests for report footer page numbering markup

### Out of scope
- invoice, estimate, statement, credit note, purchase order, and payslip footer behavior unless they share the same bug
- report content/layout changes unrelated to the footer
- non-PDF rendering

## Requirements
1. Multipage report PDFs must show the correct current page number on each page.
2. The total page count must remain visible.
3. Existing report content and table layout should remain unchanged.
4. The fix should be specific to the report template and avoid broad layout churn.

## Recommended approach
Use WeasyPrint paged-media margin boxes for the report footer instead of fixed-position footer elements. This should allow `counter(page)` and `counter(pages)` to resolve per rendered page.

## Risks
- Margin-box pagination must reserve enough footer space to avoid overlapping the report body.
- The report template is separate from the other PDF templates, so its footer solution should not be copied blindly into every document family.

## Acceptance criteria
- A multipage report no longer repeats the final page number on every page.
- The report template still renders the footer text and total page count.
- Regression tests cover the template footer mechanism.

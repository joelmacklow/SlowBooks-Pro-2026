# PRD: Align report PDF footer page count typography with footer details

## Objective
Make the report PDF page counter match the font and size of the report name details shown in the footer left area.

## Constraints
- Keep the existing correct paged-media page numbering behavior.
- Preserve the current report footer text content.
- Keep the change scoped to the report PDF template and its regressions.

## Implementation sketch
- Update the `@bottom-right` page-margin box styling in `app/templates/report_pdf.html`.
- Reuse the same font stack, size, and color used by the footer left running element.
- Leave the footer content and page count counter logic unchanged.

## Impacted files
- `app/templates/report_pdf.html`
- `tests/test_pdf_service_formatting.py`
- `tests/test_report_pdf_layout.py`

## Test plan
- Assert the report template includes the same font/size styling for the page counter and left footer.
- Run the focused PDF formatting and layout tests.
- Run diff hygiene checks.

## Risk notes
- Typography changes can slightly shift footer layout, so verify the footer still fits on all pages.

# Test Spec: Align report PDF footer page count typography with footer details

## Coverage goals
1. The report template should keep using paged-media counters for page numbers.
2. The page counter should explicitly inherit the report footer typography.
3. The footer left running element should remain unchanged.

## Assertions
- `report_pdf.html` contains `@bottom-left { content: element(report-footer); }`.
- `report_pdf.html` contains `@bottom-right` styling with the Inter font stack.
- `report_pdf.html` contains the same footer font size used by the footer left location.
- The footer counter logic still uses `counter(page)` and `counter(pages)`.

## Verification
- `python -m pytest tests/test_pdf_service_formatting.py tests/test_report_pdf_layout.py`
- `git diff --check`

# Test Spec — Fix page numbering in multipage PDF report footers

## Date
2026-04-30

## Verification targets

### 1. Template regression
Update report layout tests to assert the report template uses paged-media footer hooks, such as:
- `@bottom-left`
- `@bottom-right`
- `counter(page)`
- `counter(pages)`

### 2. Footer implementation regression
Assert the old fixed footer mechanism is removed from `report_pdf.html` to prevent the stale page-number issue.

### 3. Existing report invariants
Keep existing assertions for:
- A4 / 1.5cm page setup
- Inter font loading
- logo rendering and sizing
- table wrapping/layout markers

### 4. Optional behavior check
If feasible, add a narrow unit-level check for the page footer HTML/CSS string instead of a brittle full PDF snapshot.

## Safety checks
- `./.venv/bin/python -m pytest tests/test_pdf_service_formatting.py tests/test_report_pdf_layout.py`
- `git diff --check`

## Review focus
- current page and total pages are both represented in the report footer
- the footer mechanism is compatible with multipage rendering
- the report body still has enough bottom space for the footer

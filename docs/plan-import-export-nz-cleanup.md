# NZ Import/Export Cleanup Slice

## Summary
Finish the remaining NZ-localization cleanup in CSV and IIF import/export while preserving QuickBooks IIF wire compatibility.

## Key Changes
- Keep QuickBooks-compatible IIF structure and legacy acceptance intact.
- Localize app-owned CSV/IIF labels, descriptions, and helper behavior to NZ-first wording.
- Ensure GST-related IIF export/import behavior aligns with the current NZ GST control-account model.
- Add regression tests for CSV headers, IIF GST labels, IIF import compatibility, and IIF UI wording.

## Test Plan
- Add failing tests first for CSV export labels, IIF export GST/account wording, legacy+NZ-compatible IIF import behavior, and IIF UI copy.
- Re-run full Python/JS verification, syntax checks, and `git diff --check`.

## Defaults
- Preserve IIF wire compatibility and accept legacy labels on import.
- Prefer NZ-facing wording in app/UI/docs and CSV outputs.
- Do not redesign the IIF engine or add multi-currency changes in this slice.

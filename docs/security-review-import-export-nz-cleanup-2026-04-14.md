# Security Review — NZ Import/Export Cleanup (2026-04-14)

## Scope Reviewed
- `app/services/csv_export.py`
- `app/services/iif_export.py`
- `app/services/iif_import.py`
- `app/static/js/iif.js`
- related import/export regression tests

## Review Focus
- Whether the localization cleanup preserved QuickBooks IIF compatibility while removing stale US-facing presentation
- Whether import behavior still accepts legacy GST/account labels safely
- Whether the slice introduced any new parsing or export trust-boundary issues

## Findings
1. **IIF export now matches the current NZ GST account presentation**
   - Exported invoice/estimate GST splits now use `GST` rather than stale `Sales Tax Payable` wording.
   - This aligns exported data with the current NZ chart while keeping the underlying IIF wire structure unchanged.

2. **IIF import remains backward compatible for legacy GST labels**
   - Import still accepts `Sales Tax Payable` while also handling `GST` as a tax split account.
   - This reduces migration risk for older legacy files while keeping new NZ exports consistent.

3. **No new execution or parsing trust boundary was introduced**
   - The slice stayed within existing CSV/IIF parsing/export logic and did not add shell execution, external calls, or dynamic code evaluation.

## Residual Risks
- The broader import/export module is not yet rolled into RBAC enforcement, so these routes still sit outside the newer protected payroll/admin surfaces.
- QuickBooks IIF compatibility still constrains how far NZ-facing naming can diverge at the wire level.

## Conclusion
- No new CRITICAL/HIGH issues identified in this slice.
- Residual risk is **LOW to MEDIUM** and mainly relates to broader access-control rollout rather than the localization cleanup itself.

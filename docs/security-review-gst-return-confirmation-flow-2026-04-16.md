# Security Review — GST Return Confirmation Flow (2026-04-16)

## Scope Reviewed
- `app/models/gst_return.py`
- `app/services/gst_return_filing.py`
- `app/services/gst_settlement.py`
- `app/routes/reports.py`
- `app/static/js/reports.js`
- GST return/settlement regression tests and migration

## Review Focus
- Whether Box 9 and Box 13 adjustments are now persisted as part of a confirmed GST return record
- Whether confirmed return snapshots stay immutable and are reused for later download/settlement flows
- Whether the new flow preserves existing historical visibility for legacy settled periods

## Findings
1. **Box 9 and Box 13 are now persisted on return confirmation**
   - Confirming a GST return creates a dedicated `gst_returns` record with saved adjustments and a full Box 5–15 snapshot.
   - This removes the previous dependency on transient UI/query-string state for confirmed returns.

2. **Confirmed return snapshots are reused for later actions**
   - Summary reads for confirmed periods now come from the stored return snapshot rather than recalculating from mutable ledger data.
   - GST101A downloads for confirmed periods also use the saved return snapshot.

3. **Settlement now follows return confirmation**
   - Settlement candidates are withheld until the return is confirmed.
   - Settlement confirmation now requires a confirmed GST return first, which enforces the intended workflow ordering.

4. **Legacy historical periods remain visible**
   - Historical returns still include older periods that only exist as `gst_settlements`, so this change does not hide already-confirmed legacy data.

## Residual Risks
- Confirmed-return snapshots are intentionally immutable; amendment/void workflows for filed returns are not part of this slice.
- Transaction-tab views for confirmed periods still derive from current underlying data using the saved Box 9/13 values, not from a separately snapshotted transaction list.
- No live production migration run against PostgreSQL was exercised in this session; migration integrity relied on repository tests and model loading.

## Verification
- `.venv/bin/python -m py_compile app/models/gst_return.py app/services/gst_return_filing.py app/services/gst_settlement.py app/routes/reports.py tests/test_gst_returns_overview.py tests/test_gst_return_report.py tests/test_gst_settlement.py`
- `.venv/bin/python -m unittest tests.test_gst_returns_overview tests.test_gst_return_report tests.test_gst_settlement tests.test_alembic_migration_integrity`
- `.venv/bin/python -m unittest discover -s tests`
- `node tests/js_gst_return_report.test.js`
- `node tests/js_gst_settlement_ui.test.js`
- `for f in tests/js_*.test.js; do node "$f"; done`
- `git diff --check`

## Conclusion
- No new CRITICAL/HIGH security issues identified in this slice.
- The new confirmation flow improves data integrity and auditability by turning previously transient GST adjustments into a persisted return record while preserving the existing settlement trust boundary.

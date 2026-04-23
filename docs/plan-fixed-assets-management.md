# Fixed Assets Management Slice Plan

## Objective
Add a first complete fixed-assets workflow covering asset type setup, asset registration/detail/editing, disposal, CSV import, FY depreciation runs, and a fixed-asset reconciliation report.

## Constraints
- Fixed assets live in their own module, while the reconciliation report lives under Reports.
- Fixed assets are separate records from the chart of accounts.
- Account mappings are per asset type, with system account role support for default accumulated-depreciation and depreciation-expense accounts.
- Use existing `accounts.manage` / import-export permissions for this slice.
- Keep depreciation history/reversal and file attachments as future follow-up work.

## Implementation Sketch
- Add fixed-asset and fixed-asset-type tables plus a migration.
- Add asset-type account mappings for asset, accumulated depreciation, and depreciation expense accounts, plus defaults in system account roles.
- Implement register/edit/dispose/import/depreciation endpoints and UI flows.
- Implement FY depreciation posting using asset type mappings and derived book values.
- Add a fixed-asset reconciliation report screen under Reports.

## Impacted Files
- `alembic/versions/u1j2k3l4m5n6_add_fixed_assets_module.py`
- `app/models/fixed_assets.py`
- `app/models/__init__.py`
- `app/models/settings.py`
- `app/services/accounting.py`
- `app/services/chart_template_loader.py`
- `app/services/fixed_assets.py`
- `app/routes/fixed_assets.py`
- `app/routes/reports.py`
- `app/main.py`
- `app/static/js/fixed_assets.js`
- `app/static/js/reports.js`
- `app/static/js/app.js`
- `index.html`
- tests for fixed assets, reports, and account-role mappings

## Test Plan
- Add targeted Python tests for registration, depreciation, disposal, reconciliation, and CSV import.
- Add targeted JS tests for module rendering and reconciliation report rendering.
- Re-run relevant system-account-role and report tests.
- Run syntax checks, migration integrity checks, and `git diff --check`.

## Risk Notes
- Disposal/gain-loss journals are sensitive to sign treatment and account selection.
- Imported assets may arrive without usable asset-type mappings, so the UI must tolerate incomplete imported types.
- Without depreciation history tables yet, as-of reporting is effectively current-state focused.

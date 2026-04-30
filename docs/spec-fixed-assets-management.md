# Fixed Assets Management Slice Specification

## Goal
Provide a first complete fixed-assets workflow for registering, maintaining, depreciating, importing, disposing, and reconciling fixed assets.

## Required Behavior
- A dedicated Fixed Assets module must let users:
  - manage asset types
  - register assets
  - edit asset details
  - view a detail page for each asset
  - import assets from the provided CSV template format
  - run FY depreciation
  - sell/dispose assets
- Asset types must carry mappings for:
  - fixed asset account
  - accumulated depreciation account
  - depreciation expense account
- The existing system account mapping UI must expose default accumulated-depreciation and depreciation-expense roles for fixed assets.
- The module list view must show asset name, asset type, purchase date, purchase price, and book value.
- A Fixed Asset Reconciliation report must be available under Reports.

## Constraints
- Fixed assets remain separate from COA accounts themselves.
- Book value is derived, not manually editable.
- Depreciation history/reversal and file attachments are explicitly deferred.
- Use existing auth boundaries (`accounts.manage`, import/export permissions).

## Verification
- Targeted backend tests for journal posting, depreciation, disposal, and import behavior.
- Targeted frontend tests for module/report rendering.
- `node --check app/static/js/fixed_assets.js`
- `node --check app/static/js/reports.js`
- `git diff --check`

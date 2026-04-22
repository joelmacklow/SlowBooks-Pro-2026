# Company Snapshot Profit Trend Alignment Fix Specification

## Goal
Align the net profit/loss helper text with the rest of the profit widget content in the Company Snapshot dashboard.

## Required Behavior
- The trend/helper line under the net profit/loss value should share the same left inset as the main value and other widget content.
- Other `snapshot-trend` usages elsewhere on the dashboard should keep their current layout.
- The helper copy and profit widget data behavior must remain unchanged.

## Constraints
- Do not alter dashboard APIs, permissions, or widget ordering.
- Do not introduce new packages or broader layout changes.

## Verification
- Targeted dashboard render regression coverage for the new scoped trend hook.
- `node tests/js_dashboard_rbac_visibility.test.js`
- `node --check app/static/js/app.js`
- `git diff --check`

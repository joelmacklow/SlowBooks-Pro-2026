# Spec: expose add/edit actions in the Chart of Accounts UI

## Goal
Ensure the Chart of Accounts page lets a manager add new accounts and edit any existing account directly from the list view.

## Required Behavior
- Users with `accounts.manage` see a `New Account` button on the Chart of Accounts page.
- Users with `accounts.manage` see an `Edit` action on every account row, including seeded/system accounts.
- Editing continues to use the existing account modal/form flow and backend update endpoint.
- Users without `accounts.manage` do not see the add/edit controls.

## Verification
- JS/UI regression test for the rendered accounts page.
- `git diff --check`.

## Assumptions
- System accounts are intentionally editable in this product branch because the backend already allows updates and current seeded charts often need localization/admin adjustments.

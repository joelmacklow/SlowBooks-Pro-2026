# Plan: expose add/edit actions in the Chart of Accounts UI

## Summary
Make the Chart of Accounts list actually actionable in the UI by exposing edit actions for every account row and keeping a visible add-account action for users with account-management permission.

## Key Changes
- Show an `Edit` action for all chart entries, including seeded/system accounts, because the backend already permits account updates.
- Preserve the existing `New Account` entry point for users with `accounts.manage`.
- Keep delete behavior unchanged; this slice is about add/edit visibility only.

## Test Plan
- Add a focused JS/UI test that renders the Chart of Accounts page and asserts the New Account button plus row-level Edit actions are visible when the viewer has manage permission.
- Run the targeted JS test(s) and `git diff --check`.

## Constraints
- Do not widen delete capabilities.
- Do not change backend account permission or schema behavior.

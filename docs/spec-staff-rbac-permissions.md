# Spec: expand Staff RBAC template permissions

## Requirements summary
The Staff RBAC template should no longer be empty. It should include the requested operational permissions for viewing accounts/companies/items and managing/viewing contacts, purchasing, and sales.

## Functional requirements
- Update the `staff` role template permissions to include:
  - `accounts.view`
  - `companies.view`
  - `contacts.manage`
  - `contacts.view`
  - `items.view`
  - `purchasing.manage`
  - `purchasing.view`
  - `sales.manage`
  - `sales.view`
- Existing auth metadata APIs should reflect the updated Staff template automatically.

## File-level notes
- `app/services/auth.py` — source of truth for role templates.
- `tests/test_auth_rbac.py` — add or update a Staff template regression.

## Verification
- Targeted auth/RBAC tests.
- `git diff --check`.

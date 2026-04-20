# Plan: expand Staff RBAC template permissions

## Objective
Update the `staff` RBAC role template to include the requested operational permissions for viewing accounts/companies/items and managing/viewing contacts, purchasing, and sales.

## Requested Staff permissions
- `accounts.view`
- `companies.view`
- `contacts.manage`
- `contacts.view`
- `items.view`
- `purchasing.manage`
- `purchasing.view`
- `sales.manage`
- `sales.view`

## Current state summary
- RBAC permission definitions and role templates live in `app/services/auth.py`.
- The `staff` template currently has no default permissions (`permissions: set()`).
- Existing auth/RBAC tests already exercise role/login behavior and are the right place to lock the new template surface (`tests/test_auth_rbac.py`).

## Constraints
- Only change the `staff` template defaults; do not widen unrelated roles.
- Preserve existing permission keys and auth metadata shapes.
- Keep the change small and regression-tested.

## Implementation sketch
1. Update `ROLE_TEMPLATE_DEFINITIONS['staff']['permissions']` in `app/services/auth.py`.
2. Add/update a focused auth regression asserting the Staff role resolves the requested effective permissions.
3. Run targeted auth contract tests.

## Acceptance criteria
- Staff users inherit the requested permissions by default.
- Auth metadata/role definitions expose the updated Staff permission set.
- Existing route auth contracts remain unchanged.

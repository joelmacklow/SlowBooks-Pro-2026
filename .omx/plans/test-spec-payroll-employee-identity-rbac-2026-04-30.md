# Test Spec — Payroll Slice 1: employee identity linkage and RBAC foundation

## Date
2026-04-30

## Objective
Prove the employee identity/RBAC foundation is safe before employee self-service timesheet or payslip routes are implemented.

## Targeted test file
Add `tests/test_employee_portal_auth.py`. Reuse the in-memory SQLAlchemy style already used by `tests/test_auth_rbac.py:21-46` and import `app.models` before `Base.metadata.create_all` so the new link model is included.

## Required test setup
- Create separate in-memory company and master sessions where needed, matching `tests/test_auth_rbac.py:26-39`.
- Seed owner via `bootstrap_admin` and use `require_permissions("users.manage")` for admin actions, matching `tests/test_auth_rbac.py:77-124`.
- Create company-local `Employee` rows via `app.routes.employees.create_employee` or direct model setup, using permissions equivalent to `app/routes/employees.py:52-79`.
- Create employee users with the new `employee_self_service` role through existing user-management service/route paths.

## Unit/service tests to add first
1. `test_employee_self_service_role_is_least_privilege`
   - Assert role exists in `ROLE_TEMPLATE_DEFINITIONS`.
   - Assert it includes only self-service permissions needed by this slice/future self routes.
   - Assert it excludes `employees.view_private`, `employees.manage`, `payroll.view`, `payroll.create`, `payroll.process`, and `payroll.payslips.view`.
2. `test_link_existing_user_to_employee_for_active_company_scope`
   - Given an active user membership and active employee in the active company DB, create a link.
   - Assert the response stores `user_id`, derived `company_scope`, `employee_id`, and `is_active=True`.
3. `test_link_creation_rejects_stale_employee_id`
   - Attempt to link to an employee id that is absent in the active company DB.
   - Expect 404 or 400 with no committed link.
4. `test_link_creation_rejects_inactive_employee`
   - Attempt to link to `Employee.is_active=False`.
   - Expect rejection.
5. `test_link_creation_rejects_user_without_active_membership_for_scope`
   - Create or update a user with inactive/no membership for the active scope.
   - Expect 403 or 400.
6. `test_duplicate_active_user_scope_link_is_rejected`
   - Create one active link for `(user_id, company_scope)`.
   - Attempt a second active link for a different employee in the same scope.
   - Expect rejection and only one active link.
7. `test_duplicate_active_employee_scope_link_is_rejected`
   - Create one active link for `(company_scope, employee_id)`.
   - Attempt to link a different user to the same employee in the same scope.
   - Expect rejection and only one active link.
8. `test_inactive_historical_link_allows_relink`
   - Deactivate a link.
   - Create a new active link for the same user/employee scope as business rules allow.
   - Assert old link remains inactive and resolver chooses only the new active link.
9. `test_resolve_employee_link_returns_only_active_current_scope_link`
   - Log in as employee user and resolve self context.
   - Assert expected employee id for active company scope.
   - Assert inactive or wrong-scope links are ignored/rejected.
10. `test_resolve_employee_link_does_not_return_payroll_private_fields`
    - Assert self/link response omits IRD number, pay rate, tax code, child support, KiwiSaver, and notes.

## Route tests to add
1. `test_admin_can_list_links_for_active_scope`
   - Route requires `users.manage`.
   - Response includes user identity and minimal employee display data only.
2. `test_non_admin_cannot_link_or_unlink_employee_user`
   - An employee self-service user and payroll viewer both fail to create/deactivate links unless explicitly permissioned.
3. `test_employee_can_resolve_self_context_but_not_admin_link_list`
   - `GET /api/employee-portal/self` works for linked employee user.
   - Link management routes fail with 403.
4. `test_cross_company_header_without_membership_is_rejected`
   - Reuse the `X-Company-Database` pattern covered in `tests/test_auth_company_access_controls.py:56-69`.
   - Attempt link/self resolution for a company where the user lacks membership; expect 403.

## Existing regression tests to run
- `npm test -- tests/test_employee_portal_auth.py`
- `npm test -- tests/test_auth_rbac.py tests/test_auth_company_access_controls.py tests/test_staff_role_template_permissions.py`

## Security assertions
- No test should rely on client-provided employee ownership for self context; resolution must come from `AuthContext` and the active link.
- Negative tests must cover unauthenticated, wrong permission, inactive user, inactive membership, stale employee, inactive employee, duplicate active user link, duplicate active employee link, and wrong company scope.
- Link-list responses must not serialize `EmployeeResponse` directly if that includes private payroll fields.
- No logs or exception messages should include raw session tokens, passwords, IRD numbers, or pay rates.

## Manual smoke after implementation
1. Bootstrap owner.
2. Create active hourly employee.
3. Create `employee_self_service` user for the same active company scope.
4. Link the user to the employee.
5. Log in as employee user.
6. Resolve `/api/employee-portal/self` and confirm only minimal own employee context is returned.
7. Confirm employee user receives 403 for employee admin list/create and employee-link management routes.

## Acceptance gate for moving to Slice 2
- Targeted tests pass.
- Existing auth/RBAC/company-scope tests pass.
- `git diff --check` passes.
- Explicit security review finds no known IDOR, scope, permission-escalation, or payroll-PII response issue.

# PRD — Payroll Slice 1: employee identity linkage and RBAC foundation

## Date
2026-04-30

## Objective
Deliver the first implementation slice for payroll timesheets by adding the master-auth-side employee identity link, self-service role/permissions, and API-first admin link management needed before any employee timesheet or self-payslip route can safely exist.

## Slice status
- Parent feature plan: `.omx/plans/prd-payroll-timesheets-2026-04-30.md`.
- Parent test spec: `.omx/plans/test-spec-payroll-timesheets-2026-04-30.md`.
- Parent todo: `.omx/plans/todo-payroll-timesheets-2026-04-30.md`.
- This slice should be executed on a task branch such as `feat/payroll-employee-identity-rbac` after this planning branch is merged or rebased.

## Current-state evidence
- Auth users, memberships, sessions, and permission overrides are master-side models in `app/models/auth.py:9`, `app/models/auth.py:24`, `app/models/auth.py:46`, and `app/models/auth.py:62`.
- Current membership uniqueness is scoped to one `UserMembership` per `(user_id, company_scope)` at `app/models/auth.py:24-28`; employee identity needs a separate link because `Employee` lives in a company database.
- The active request scope is already normalized through `app/services/auth.py:242-265`, and `get_auth_context` binds a session to an active membership at `app/services/auth.py:372-406`.
- `require_permissions` validates permission keys and enforces missing permissions at `app/services/auth.py:424-445`; new self-service permissions must be registered before route dependencies can use them.
- Role templates currently include owner, operations admin, payroll admin/viewer, and staff in `app/services/auth.py:61-138`; no employee self-service role exists yet.
- Existing payroll/private employee APIs require broad admin permissions such as `employees.view_private` and `employees.manage` in `app/routes/employees.py:28-79`.
- The company-local payroll `Employee` model is in `app/models/payroll.py:30-63`, so the employee link must store a company-local `employee_id` rather than a normal cross-database foreign key.
- Company scope choices are surfaced by `list_company_scope_options` in `app/services/company_service.py:65-82`.
- Route registration is centralized in `app/main.py:24-41` and `app/main.py:81-124`.
- Existing auth/RBAC tests to extend are `tests/test_auth_rbac.py:21-199`, `tests/test_auth_company_access_controls.py:19-70`, and role template coverage in `tests/test_staff_role_template_permissions.py:13-28`.
- Code-review graph planning context: 3,340 nodes / 33,087 edges; projected auth/payroll identity changes are high risk and affect the `bootstrap_admin`, `login`, `create_user`, and `update_user` flows.

## Requirements summary
1. Add an `EmployeePortalLink` (or equivalently named) master-auth-side model that maps `user_id + company_scope` to a company-local `employee_id`.
2. Keep link resolution server-side and scope-derived; employee self-service routes in later slices must never trust client-supplied ownership.
3. Add employee self-service permission definitions and a least-privilege role template without granting existing payroll/admin permissions.
4. Provide API-first admin link management for the active company scope: create/link, list, deactivate/unlink, and resolve current user context.
5. Validate employee existence in the active company database before creating or resolving a link.
6. Prevent ambiguous active links, including two active employees for one `(user_id, company_scope)` and two active users for one `(company_scope, employee_id)`.
7. Preserve existing owner, payroll admin, payroll viewer, staff, bootstrap, login, and company-scope behavior.

## Non-goals for this slice
- No timesheet tables, lifecycle service, or employee timesheet routes.
- No payslip self-service route implementation; only register the future self-payslip permission if the parent feature needs it.
- No employee portal frontend.
- No email invite delivery. A link-to-existing-user and optional account-creation helper are enough for MVP.
- No cross-company arbitrary DB opening from client-provided payloads; link management should operate on the authenticated active company scope.

## Constraints
- Store the link in the master/auth database alongside `User` and `UserMembership` (`app/models/auth.py:9-74`), not in company-local payroll tables.
- Do not add a database FK from the link to `employees.id`; `Employee` is company-scoped (`app/models/payroll.py:30-63`).
- Do not broaden existing payroll viewer/admin roles beyond their current explicit permissions in `app/services/auth.py:100-122`.
- Any route dependency using new permissions must work with `validate_permission_keys` (`app/services/auth.py:209-216`).
- Keep route changes thin; put link validation/resolution in a service so future timesheet routes can reuse it.
- Preserve the existing `X-Company-Database` scope behavior enforced by `get_auth_context` and `get_db` (`app/services/auth.py:372-406`, `app/database.py:85-98`).

## Implementation sketch
1. **Tests first**
   - Add `tests/test_employee_portal_auth.py` focused on the link model/service, self-service permissions, and route-level negative checks.
   - Add or extend a role-template test proving the employee role excludes `employees.view_private`, `employees.manage`, `payroll.view`, `payroll.create`, `payroll.process`, and `payroll.payslips.view`.
2. **Model + migration**
   - Extend `app/models/auth.py` with `EmployeePortalLink` fields: `id`, `user_id`, `company_scope`, `employee_id`, `is_active`, `created_at`, `updated_at`, `created_by_user_id`, `deactivated_at`, `deactivated_by_user_id`.
   - Add relationships from `User` for owned employee links and creator/deactivator links where useful.
   - Add the model to `app/models/__init__.py`.
   - Add an Alembic migration after current head `w2k3l4m5n6o7` that creates `employee_portal_links` in the auth/master schema.
   - Prefer partial unique indexes for active links:
     - active `(user_id, company_scope)` unique;
     - active `(company_scope, employee_id)` unique.
3. **Permissions + role**
   - Add permission definitions for `timesheets.self.view`, `timesheets.self.create`, `timesheets.self.submit`, and `payroll.self.payslips.view`; optionally reserve `employee_links.manage` if link management should be narrower than `users.manage`.
   - Add `employee_self_service` role with only self-service permissions.
   - Ensure `owner` automatically receives new permissions via the existing all-permissions template.
4. **Service seam**
   - Add `app/services/employee_portal.py` with helpers similar to:
     - `create_employee_link(master_db, company_db, user_id, employee_id, auth_context)`;
     - `deactivate_employee_link(master_db, link_id, auth_context)`;
     - `list_employee_links(master_db, company_db, company_scope)`;
     - `resolve_employee_link(master_db, company_db, auth_context, *, required=True)`.
   - Derive `company_scope` from `auth_context.membership.company_scope`, not from a trusted client-owned field.
   - Validate that linked users have an active membership for the scope and that `Employee.id` exists and is active in the company DB.
5. **API-first routes**
   - Add a small router such as `app/routes/employee_portal.py` and register it in `app/main.py`.
   - Admin endpoints should require `users.manage` initially to align with existing user-management APIs at `app/routes/auth.py:149-191`.
   - Proposed endpoints:
     - `GET /api/employee-portal/links` list links for active scope;
     - `POST /api/employee-portal/links` link existing user to employee in active scope;
     - `POST /api/employee-portal/links/{link_id}/deactivate` deactivate/unlink;
     - `GET /api/employee-portal/self` resolve the authenticated employee link for later self-service smoke tests.
6. **Schemas**
   - Add `app/schemas/employee_portal.py` for link create/list/self responses, keeping payroll PII minimal: link id, user id/email/name, employee id/name/status, company scope, active state, timestamps.
7. **Safety review and handoff**
   - Verify no route returns IRD number, pay rate, or full payroll private fields in link-list responses.
   - Leave later timesheet and payslip self-service routes blocked until `resolve_employee_link` has negative tests.

## Impacted files and likely blast radius
- `app/models/auth.py` — add master-side `EmployeePortalLink` and user relationships.
- `app/models/__init__.py` — import/export new model for metadata creation.
- `alembic/versions/<new>_add_employee_portal_links.py` — create table and active-link uniqueness indexes.
- `app/services/auth.py` — register self-service permissions and role template.
- `app/services/employee_portal.py` — new reusable link management/resolution service.
- `app/schemas/employee_portal.py` — new request/response schemas.
- `app/routes/employee_portal.py` — new API-first link/self-context routes.
- `app/main.py` — register router.
- `tests/test_employee_portal_auth.py` — new targeted tests.
- `tests/test_auth_rbac.py` and/or `tests/test_staff_role_template_permissions.py` — focused regression coverage for role/permission behavior.

## Acceptance criteria
1. A `users.manage` actor can link an existing active user to an active employee in the currently authorised company scope.
2. Link creation fails when the user lacks an active membership for the current scope.
3. Link creation fails when `employee_id` does not exist or is inactive in the active company DB.
4. The system prevents duplicate active links for both `(user_id, company_scope)` and `(company_scope, employee_id)`.
5. Deactivating a link makes `resolve_employee_link` fail for that employee user.
6. An `employee_self_service` user has self-service permissions and does not have broad employee/payroll admin permissions.
7. Existing bootstrap, login, user creation/update, payroll viewer, payroll admin, and company-scope access tests still pass.
8. Link list/self responses do not expose IRD numbers, pay rates, tax codes, or payslip/pay-run details.

## Verification steps
- `npm test -- tests/test_employee_portal_auth.py`
- `npm test -- tests/test_auth_rbac.py tests/test_auth_company_access_controls.py tests/test_staff_role_template_permissions.py`
- If route registration is added, run an import/smoke check through the targeted tests that instantiate route functions.
- `git diff --check`
- Security review: auth boundaries, cross-company scoping, stale/inactive users/employees, duplicate active links, payroll PII in responses/logs.

## Risk notes
- **High risk — auth scope regression:** Changes to permissions and roles can affect all guarded routes because `require_permissions` is a central dependency. Mitigation: keep permission additions additive and run existing auth/RBAC tests.
- **High risk — IDOR/cross-company leak:** Employee links are a bridge from auth to payroll PII. Mitigation: derive scope from `AuthContext`, validate active membership, and do not trust client-supplied `employee_id` for self routes.
- **Medium risk — partial unique index portability:** Active-only uniqueness needs SQLite/Postgres-compatible migration syntax. Mitigation: add service-level duplicate checks and DB indexes; verify with SQLite tests.
- **Medium risk — exposing payroll PII:** Link listing could accidentally serialize full `EmployeeResponse`. Mitigation: use dedicated minimal schemas.

## Open decisions resolved for this slice
- **Invite flow:** defer email invite delivery; support link existing user and optional create-user-then-link path using existing `/api/auth/users` capabilities.
- **Company scope:** derive link scope from authenticated active company scope. Admins switch company scope with existing company header/session behavior instead of posting arbitrary target scopes.
- **Own payslip permission:** reserve `payroll.self.payslips.view` now so Slice 3 can implement self-payslip routes without broad payroll permissions.

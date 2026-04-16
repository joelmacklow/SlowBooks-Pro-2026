# PRD — Per-user company access controls

## Date
2026-04-17

## Problem
The auth model already contains a `company_scope` concept, but the current permissions system behaves like a single-company access model. Users cannot be explicitly granted or denied access to specific companies, and company switching does not enforce per-user access boundaries.

## Goal
Allow administrators to control which companies each user may access, and enforce those controls when users switch company context.

## Requirements
- Support per-user company access assignments using the existing membership/company-scope model.
- Allow admins to choose accessible companies for a user in the Users & Access UI.
- Reuse the selected role/permission overrides across each granted company scope for this slice.
- Enforce company access when a selected company is requested through authenticated business routes.
- Deny access to companies for which the user has no active membership.
- Preserve current single-company behavior for existing users by treating the current/default company as accessible unless explicitly changed through the new UI.

## Non-goals
- Different roles per company in the same edit flow.
- Company-specific permission overrides beyond the copied role/override set in this slice.
- Full company-aware login/session switcher UX on the auth pages.

## Acceptance criteria
1. Admin can assign one or more accessible companies to a user.
2. Auth metadata/UI exposes the available company scopes.
3. User create/update persists memberships for the selected companies.
4. Requests against a selected company succeed only when the user has access to that company scope.
5. Requests against an unassigned company return 403.
6. Existing current/default company access still works for users who retain that scope.

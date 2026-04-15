# Spec: Add an admin-only NZ demo data load action

## Deliverable
Add a protected UI action that lets admins trigger the existing NZ demo business
seed from inside the app.

## Rules
- The backend route must require `settings.manage`.
- The route must reuse the existing NZ demo seed script entry point.
- The Settings UI must expose the action only through the existing admin-only
  Settings page.
- Tests must fail if the button disappears or the route is no longer protected.

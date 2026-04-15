# Add an admin-only NZ demo data load action

## Summary
Expose the existing NZ demo business seed as a protected admin action inside the
Settings UI so admins can load demo data without dropping to the shell.

## Key Changes
- Add an admin-only backend route that runs the existing NZ demo seed script.
- Add a Settings page action/button that invokes the route.
- Keep the demo seed idempotent and reuse the existing script rather than
  duplicating seed logic in the route.

## Test Plan
- Add a backend test that verifies the route requires `settings.manage` and
  calls the demo seed entry point.
- Add a JS test that verifies the Settings page renders the action and posts to
  the new endpoint.
- Run the focused Python and JS tests plus `git diff --check`.

## Defaults
- The load action should live in the admin Settings page.
- Only users with `settings.manage` should be able to trigger it.

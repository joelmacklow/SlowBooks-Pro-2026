# Prevent route imports from referencing missing schema modules

## Summary
Add a regression check for route-to-schema imports and remove the dead bank
import schema reference that currently breaks app startup.

## Key Changes
- Add a test that scans route imports for `app.schemas.*` modules and verifies
  the referenced schema files exist.
- Remove the unused `app.schemas.bank_import` import from the bank import route.

## Test Plan
- Run `python -m unittest tests.test_route_schema_imports tests.test_batch_payment_schema tests.test_docker_config`.
- Run `git diff --check`.

## Defaults
- Route modules should only import schema modules that actually exist in
  `app/schemas`.

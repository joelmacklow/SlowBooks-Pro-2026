# Spec: Rename Demo Seed Script

## Deliverable
Rename the current NZ demo-data seed script to a filename that reflects its current purpose.

## Rules
- Update all tracked repo references to the old filename.
- Preserve script behavior and CLI usage other than the new path/name.
- Do not use this slice to change the seeded data itself.

## Validation
- No remaining tracked references to the old filename.
- Renamed script compiles.
- `git diff --check` passes.

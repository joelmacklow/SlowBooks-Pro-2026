# Rename Demo Seed Script

## Summary
Rename the legacy demo seed script filename so it matches its current NZ demo-data purpose, then update all repo references.

## Key Changes
- Rename `scripts/seed_nz_demo_data.py` to an NZ-appropriate filename.
- Update README/docs and any script/tool references.
- Preserve behavior; this is a naming/clarity cleanup only.

## Test Plan
- Verify no stale references remain.
- Run `py_compile` on the renamed script.
- Run `git diff --check`.

## Defaults
- Keep the script content unchanged except for filename/path references.

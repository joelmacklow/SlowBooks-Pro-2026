# INSTALL.md Documentation Slice

## Summary
Add a dedicated root `INSTALL.md` that centralizes installation/bootstrap instructions for local Python, Docker self-contained, and Docker/external-Postgres setups, then slim README down to point to it.

## Key Changes
- Add `INSTALL.md` at repo root.
- Cover prerequisites, local install, Docker install, external Postgres env configuration, migrations/seeding, backup notes, and first-run verification.
- Add a pointer from `README.md` to `INSTALL.md`.

## Test Plan
- Verify the file exists and references current env/docker/runtime commands.
- Run `git diff --check`.

## Defaults
- README remains the product overview + quick start surface.
- INSTALL.md becomes the detailed installation reference.

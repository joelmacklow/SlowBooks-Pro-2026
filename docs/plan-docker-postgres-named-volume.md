# Move bundled Docker Postgres to a named volume

## Summary
Replace the bundled Postgres host-path bind mount with a Docker-managed named
volume so the default stack starts reliably across Linux hosts without manual
ownership or SELinux directory preparation.

## Key Changes
- Change the compose Postgres storage from a local path mount to
  `postgres_data:/var/lib/postgresql`.
- Keep the app source bind mount, including `:Z`, for live code edits.
- Add regression coverage that locks the named volume declaration in place.
- Update Docker docs to describe the named volume and the new reset flow.

## Test Plan
- Run `python -m unittest tests.test_docker_config`.
- Run `docker compose config`.
- Run `git diff --check`.

## Defaults
- The bundled Postgres service should use the Docker-managed `postgres_data`
  volume by default.
- Old local folders from previous compose layouts are no longer used
  automatically by the bundled database.

# Align Docker Postgres 18 volume layout

## Summary
Update the bundled Docker Postgres bind mount to the parent directory layout
expected by the `postgres:18` image so local startups stop failing on the old
`/var/lib/postgresql/data` mount pattern.

## Key Changes
- Change the compose Postgres bind mount from `./data/postgres:/var/lib/postgresql/data`
  to `./data/postgresql:/var/lib/postgresql`.
- Add a regression test that locks the compose file to the new Postgres 18
  layout.
- Update Docker docs to point at the new local data path and warn that the old
  `./data/postgres` folder is no longer used automatically.

## Test Plan
- Run `python -m unittest tests.test_docker_config`.
- Run `git diff --check`.

## Defaults
- Fresh local Docker startups should initialize Postgres 18 under
  `./data/postgresql`.
- Existing data in the old `./data/postgres` path requires an explicit
  migration/upgrade decision instead of silently blocking container startup.

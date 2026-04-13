# Pin Docker Postgres to v18

## Summary
Pin the Docker/self-contained stack to PostgreSQL 18 instead of `latest` so local persisted data does not unexpectedly cross major versions without an intentional pg_upgrade path.

## Key Changes
- Change the compose Postgres image from `postgres:latest` to `postgres:18` and keep it pinned.
- Update install/docs/spec text that currently says latest Postgres or older bundled Postgres versions where it refers to the bundled Docker stack.
- Clarify that moving persisted Docker data between major Postgres versions requires an explicit upgrade path.

## Test Plan
- Verify no remaining `postgres:latest` references.
- Run `git diff --check`.
- Re-run Docker/config tests.

## Defaults
- The self-contained Docker stack is pinned to Postgres 18 and should not float across major versions automatically.
- External Postgres remains user-controlled through env configuration.

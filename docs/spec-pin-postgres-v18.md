# Spec: Pin Docker Postgres to v18

## Deliverable
Update the self-contained Docker stack to use `postgres:18`.

## Rules
- `docker-compose.yml` must use `postgres:18`.
- Documentation should stop describing the bundled DB as "latest Postgres" and should note the major-version pin rationale.
- Where docs mention upgrade risk, note that moving persisted data across major Postgres versions requires an explicit upgrade process such as pg_upgrade.
- Do not change the external Postgres env contract.

# Spec: Align Docker Postgres 18 volume layout

## Deliverable
Update the self-contained Docker stack to use the Postgres 18 parent-directory
mount layout.

## Rules
- `docker-compose.yml` must mount the bundled database at
  `./data/postgresql:/var/lib/postgresql`.
- Tests must fail if the compose file regresses to mounting
  `/var/lib/postgresql/data` directly.
- README and INSTALL docs must reference the new local data path and note that
  the old `./data/postgres` folder is not reused automatically.
- Do not change the app container, external Postgres env contract, or bootstrap
  behavior.

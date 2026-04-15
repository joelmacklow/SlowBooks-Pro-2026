# Spec: Move bundled Docker Postgres to a named volume

## Deliverable
Update the self-contained Docker stack so the bundled Postgres service stores
its data in a Docker-managed named volume instead of a host-path bind mount.

## Rules
- `docker-compose.yml` must mount Postgres as
  `postgres_data:/var/lib/postgresql`.
- `docker-compose.yml` must declare the `postgres_data` named volume.
- The app source bind mount must remain `./:/app:Z`.
- Tests must fail if the compose file regresses to a host-path Postgres mount.
- README and INSTALL docs must explain that old `./data/postgres` and
  `./data/postgresql` folders are no longer used by the bundled database.

# Spec: Fix Docker bind-mount permissions on SELinux hosts

## Deliverable
Update the bundled Docker compose stack so its local bind mounts are usable on
SELinux-enabled Linux hosts.

## Rules
- `docker-compose.yml` must mount the repo as `./:/app:Z`.
- `docker-compose.yml` must mount the bundled Postgres data path as
  `./data/postgresql:/var/lib/postgresql:Z`.
- Tests must fail if either bind mount loses its `:Z` relabel option.
- README and INSTALL docs must note that the relabeling prevents Docker
  `Permission denied` failures on SELinux hosts.
- Do not change the app bootstrap flow or external Postgres env contract.

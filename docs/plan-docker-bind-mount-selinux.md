# Fix Docker bind-mount permissions on SELinux hosts

## Summary
Make the bundled Docker stack work on SELinux-enabled Linux hosts by relabeling
the app and Postgres bind mounts, which avoids startup failures when the app
opens the entrypoint script and when Postgres initializes its data directory.

## Key Changes
- Add Docker's `:Z` relabel flag to the app source bind mount.
- Add Docker's `:Z` relabel flag to the Postgres data bind mount.
- Lock the compose file to those mount options with a regression test.
- Document why the relabeling exists and which permission errors it prevents.

## Test Plan
- Run `python -m unittest tests.test_docker_config`.
- Run `docker compose config`.
- Run `git diff --check`.

## Defaults
- The self-contained Docker stack should start on SELinux-enabled Linux hosts
  without requiring manual `chmod`, `chown`, or ad hoc `chcon` steps.

# Fix Docker bootstrap import path

## Summary
Ensure the app container can import the `app` package when it runs
`python scripts/bootstrap_database.py` during startup.

## Key Changes
- Add an image-level Python path that includes `/app`.
- Harden `scripts/bootstrap_database.py` so it adds the repo root to `sys.path`
  before importing `app`.
- Lock both behaviors with regression tests in the Docker config test suite.

## Test Plan
- Run `python -m unittest tests.test_docker_config`.
- Run `git diff --check`.

## Defaults
- Any Python process started inside the app container should resolve imports
  from the repository root at `/app`.
- The bootstrap script should also resolve `app` correctly when run directly
  from the repo checkout outside Docker.

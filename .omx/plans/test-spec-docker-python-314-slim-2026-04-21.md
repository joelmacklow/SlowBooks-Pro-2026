# Test Spec — Docker Python 3.14 slim update

## Date
2026-04-21

## Verification
- Confirm `Dockerfile` now uses `python:3.14-slim`.
- Run a Docker build if the host has Docker available.
- Run `git diff --check`.

## Safety checks
- Keep the diff limited to Docker-specific files plus required planning artifacts.
- Do a quick security pass to ensure no extra packages, ports, or privilege changes were introduced.

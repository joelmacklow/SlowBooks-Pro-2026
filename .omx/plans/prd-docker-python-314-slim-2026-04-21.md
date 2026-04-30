# PRD — Docker Python 3.14 slim update

## Date
2026-04-21

## Objective
Update the repo's Docker image to use a Python 3.14 slim base image instead of Python 3.12 slim.

## Current-state evidence
- `Dockerfile:1` currently uses `FROM python:3.12-slim`.
- `docker-compose.yml:16-19` builds the app image from the repo `Dockerfile`, so the Dockerfile base image controls the runtime Python version for local container workflows.

## Requirements
- Use a Python 3.14 slim base image in the app Dockerfile.
- Keep the rest of the container build logic unchanged unless Python 3.14 compatibility requires a small supporting adjustment.
- Preserve the current runtime packages and entrypoint behavior.

## Approach
- Change the Dockerfile base image from `python:3.12-slim` to `python:3.14-slim`.
- Verify the updated Dockerfile remains syntactically valid and, if Docker is available, that the image builds successfully.

## Acceptance criteria
1. `Dockerfile` references `python:3.14-slim`.
2. The Docker build definition still installs dependencies and preserves the existing entrypoint.
3. No unrelated container/config changes are introduced.

## Risks
- Python 3.14 can expose wheel/build differences for some Python packages during `pip install`.
- The slim image lineage may change Debian package availability over time, so a real build verification is preferred when Docker is available.

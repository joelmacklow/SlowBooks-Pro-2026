# PRD — Repo cleanup for code-review-graph/tool excludes

## Date
2026-04-21

## Objective
Tighten repo ignore rules so generated local-tooling directories do not sit in the repository root unaccounted for and are less likely to interfere with code-review-graph and similar repository-scanning tools.

## Current-state evidence
- The repo root contains large generated directories like `.venv/`, `.pytest_cache/`, and `.code-review-graph/`.
- Root `.gitignore` currently ignores `__pycache__/`, `*.db`, `.omx/`, and other artifacts, but does not explicitly list `.venv/`, `.pytest_cache/`, `.code-review-graph/`, or NFS cleanup files.
- `.dockerignore` already excludes `.venv` and `.pytest_cache`, which suggests these are expected to stay out of normal project scanning/build contexts.

## Requirements
- Add explicit ignore coverage for large generated directories and stale NFS temp files in the repo root.
- Keep the cleanup limited to ignore/config hygiene; do not change application behavior.
- Preserve tracked source directories and existing workflows.

## Acceptance criteria
1. Root `.gitignore` explicitly ignores `.venv/`, `.pytest_cache/`, `.code-review-graph/`, and `.nfs*`.
2. No application code or runtime behavior changes are introduced.
3. Verification demonstrates the ignore file is syntactically clean and the diff is minimal.

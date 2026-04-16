# Plan: resolve the WeasyPrint/pydyf dependency conflict

## Summary
Fix the install-time conflict caused by `weasyprint==68.0` requiring `pydyf>=0.11.0` while `requirements.txt` still pins `pydyf==0.9.0`.

## Key Changes
- Update the Python dependency pin so the WeasyPrint 68 requirement graph is internally consistent.
- Keep the change minimal and avoid unrelated dependency churn.
- Verify that a clean pip install from `requirements.txt` succeeds after the change.

## Test Plan
- Create an isolated temporary virtualenv and run `pip install -r requirements.txt`.
- Run at least targeted repo verification around Docker/dependency config, then `git diff --check`.

## Constraints
- No broad dependency upgrades beyond what is needed to resolve the explicit conflict.
- Preserve current app behavior and existing package choices where possible.

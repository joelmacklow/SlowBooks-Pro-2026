# Spec: resolve the WeasyPrint/pydyf dependency conflict

## Goal
Make `requirements.txt` installable again by aligning the explicit `pydyf` pin with the already-pinned `weasyprint==68.0` dependency requirements.

## Required Behavior
- `requirements.txt` must no longer pin a `pydyf` version that conflicts with WeasyPrint 68.
- A clean pip install from `requirements.txt` in an isolated environment must succeed.
- No unrelated dependency pins should change in this slice.

## Verification
- Temporary virtualenv install of `requirements.txt`.
- Targeted repo checks plus `git diff --check`.

## Assumptions
- The intended WeasyPrint version remains `68.0`; the stale/conflicting package is the explicit `pydyf` pin.

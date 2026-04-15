# Exception Exposure Hardening Specification

## Goal
Ensure `companies.py` and `csv.py` do not expose internal exception details, stack-adjacent text, or sensitive backend context to API clients.

## Required Behavior
- Company creation should keep intentional validation/business-rule messages but must not expose raw backend exception text for unexpected failures.
- CSV import endpoints must not leak decode errors or unexpected importer exception text in HTTP responses.
- Unexpected failures should be logged only implicitly through existing server mechanisms and surfaced to clients with generic safe details.
- Normal successful company creation and CSV import behavior must remain unchanged.

## Constraints
- Keep changes localized to the affected routes and related tests/service contract.
- No new dependencies.
- Preserve safe, user-actionable messages where they are already part of intended validation behavior.

## Verification
- Backend tests proving sensitive exception text is not returned from company creation and CSV import routes.
- Full Python suite, JS tests, syntax checks, and `git diff --check`.

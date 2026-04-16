# PRD — Companies page default entry and database-name suggestion

## Date
2026-04-17

## Problem
The Companies page only lists extra company records and omits the default/current company, which makes the company roster look incomplete. The New Company modal also requires manual database-name entry even though it can be sensibly derived from the company name.

## Goals
1. Show the default company in the Companies page list.
2. Auto-suggest a valid `database_name` as the user types a company name.

## Requirements
- The companies API/UI should include a card for the default/current company.
- The default company card should use the current database and clearly identify it.
- The New Company modal should auto-fill `database_name` from the company name using the existing naming constraints (lowercase letters, numbers, underscores).
- Auto-suggestion should not fight manual edits once the user intentionally changes the database name.

## Acceptance criteria
1. Companies page shows the default company alongside additional companies.
2. Default company card remains selectable/switchable like the others.
3. Typing `Acme Books Ltd` suggests `acme_books_ltd` in the database field.
4. Manual edits to the database field are preserved and not overwritten by later company-name typing.

# PRD — Companies dashboard navigation and switching bugfixes

## Date
2026-04-17

## Problem
Two company-management interactions are broken:
1. Clicking the Companies menu link from the dashboard does not navigate to the Companies page.
2. Using Switch To on the Companies page appears to do nothing, so users cannot actually change company context.

## Goal
Restore working navigation to the Companies page and make company switching visibly and functionally change the active company context.

## Requirements
- Fix the dashboard/shell Companies navigation so it routes to `#/companies`.
- Make company switching persist and affect subsequent API requests/app context.
- Preserve existing company list/create behavior.
- Keep the implementation minimal and aligned with the current SPA/auth architecture.

## Acceptance criteria
1. Clicking the Companies nav/menu entry routes to the Companies page.
2. Switching a company updates the stored selected company.
3. API requests include the selected company context after switching.
4. The app reload/navigation path after switching clearly lands in the selected company context.

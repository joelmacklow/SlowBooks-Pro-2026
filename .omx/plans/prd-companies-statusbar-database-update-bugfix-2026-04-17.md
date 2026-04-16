# PRD — Companies status-bar database update bugfix

## Date
2026-04-17

## Problem
After switching companies, the status bar does not update its displayed database/company indicator, leaving stale company context visible even though switching now works.

## Goal
Make the status bar immediately reflect the active company/database after company switches and during app initialization.

## Requirements
- The status bar must update when a selected company is active.
- The status bar should show the active database name even when company settings are blank or still defaulted.
- The change should preserve existing company-name display behavior where available.

## Acceptance criteria
1. Switching company updates the status bar immediately.
2. Initial app load reflects the selected company/database in the status bar.
3. If company_name is blank/default, the selected database name still appears.

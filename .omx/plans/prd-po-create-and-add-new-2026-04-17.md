# PRD — Purchase Order create-and-add-new workflow

## Date
2026-04-17

## Problem
The new PO detail workflow now supports create-and-dispatch actions, but there is no quick path for entering several purchase orders in a row. Users also want the main create action simplified to just “Create”.

## Goal
Keep the main new-PO action concise and add a one-click action that saves the current PO and immediately resets the editor to a fresh PO form.

## Requirements
- On a new PO, relabel the primary submit button to `Create`.
- Add a `Create & Add New` action for new POs.
- `Create & Add New` must save the PO via the normal validation/save path, then reload a fresh blank PO detail form.
- Existing saved-PO update behavior must remain unchanged.
- Existing create-and-dispatch actions must remain unchanged.

## Acceptance criteria
1. New PO detail screen shows `Create`, `Create & Add New`, `Create & Print / PDF`, and `Create & Email`.
2. `Create` saves and returns to the PO list as before.
3. `Create & Add New` saves and reloads a fresh new PO detail state.
4. Saved POs still show update-oriented actions instead of create-oriented actions.

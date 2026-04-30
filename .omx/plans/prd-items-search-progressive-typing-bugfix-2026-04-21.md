# PRD — Items search progressive typing bugfix

## Date
2026-04-21

## Objective
Fix the Items & Services search input so users can type progressively instead of only getting a single-character search interaction.

## Problem
The current search implementation re-renders the whole page on each input event. That disrupts normal typing flow and effectively limits the search field to one character at a time.

## Requirements
- Searching must support normal progressive typing across multiple characters.
- Keep the existing search behavior and result rendering.
- Preserve New Item/Edit flows and the lightweight toolbar design.

## Acceptance criteria
1. Typing successive characters updates the search query progressively.
2. The input remains usable across consecutive keystrokes.
3. Search results continue to refresh correctly for matching and no-match cases.

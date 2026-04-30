# PRD — Vendor-assigned items for purchase orders

## Date
2026-04-17

## Problem
The purchase-order editor currently offers every active item/service regardless of vendor, which slows data entry and makes it easier to choose irrelevant items. The item/service form also has no way to record which vendor supplies an item.

## Goal
Allow items/services to be assigned to a vendor and make the PO item picker prefer only items assigned to the selected vendor.

## Requirements
- Add an optional vendor assignment to items/services.
- Update the item/service modal so a vendor can be chosen for an item/service.
- Expose assigned vendor information through item APIs.
- Support filtering items by vendor in the items API.
- In the PO editor, when a vendor is selected, the item dropdowns should show only items assigned to that vendor.
- Keep manual line description entry available even if a vendor has no assigned items.
- Editing an existing PO should still render its saved lines even if some saved items are outside the current vendor filter.

## Acceptance criteria
1. Admin/user with item permissions can set or clear a vendor on an item/service.
2. Item create/update persists the selected vendor.
3. Item list API can filter by vendor.
4. PO editor reloads/filter item options when vendor changes.
5. PO line item dropdowns show only the selected vendor's assigned items.
6. Existing PO lines continue to render correctly when editing saved POs.

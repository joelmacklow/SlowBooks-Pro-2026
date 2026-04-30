# PRD — NZ receipts, undeposited funds, batch payments, and register cleanup

## Date
2026-04-21

## Objective
Clean up the customer receipt and banking-adjacent workflows so they better match modern New Zealand payment reality: no cheques, mostly bank-to-bank EFT, EFTPOS/card settlements, and some cash receipts.

## Current-state evidence
- Customer receipts are entered via `PaymentsPage` in `app/static/js/payments.js:90-189`, with manual invoice allocation and optional `deposit_to_account_id`.
- Receipt posting in `app/routes/payments.py:71-147` debits either the chosen deposit account or `Undeposited Funds / Receipt Clearing` (`get_undeposited_funds_id` in `app/services/accounting.py:315-325`).
- Deposits are a separate explicit workflow in `app/routes/deposits.py:17-106` and `app/static/js/deposits.js:1-69`, built around clearing pending customer receipts from Undeposited Funds into a bank asset account.
- Batch payments currently mean **customer** receipt batching in `app/routes/batch_payments.py:18-69` and `app/static/js/batch_payments.js:1-129`, not supplier/AP file payments.
- “Check Register” is a running register over asset-account journal lines in `app/routes/banking.py:742-784` and `app/static/js/check_register.js:1-47`; it is not actually cheque-specific beyond naming.
- The current receive-payment and batch-payment UIs already removed cheque-specific options in favor of `EFT`, `Cash`, and `Credit` (`app/static/js/payments.js:110-114`, `app/static/js/batch_payments.js:33-37`), but the naming and flow still reflect older QuickBooks mental models.

## External evidence
- Xero NZ states that bank feeds pull in statement data and automatically suggest matches for invoices, bills, and payments during reconciliation, which supports a bank-feed-first workflow for electronic receipts rather than forcing duplicate manual entry. Source: Xero NZ bank reconciliation page (`https://www.xero.com/nz/accounting-software/reconcile-bank-transactions/`).
- Xero also positions bulk reconciliation / cash coding as the way to process many cash-style statement lines, creating receive/spend money transactions from bank lines. Source: same Xero NZ reconciliation page.
- Xero’s Tap to Pay flow marks invoices paid and leaves them “ready for reconciliation,” which reinforces the model that operational receipt capture and bank settlement matching are separate steps. Source: Xero AU Tap to Pay page (`https://www.xero.com/au/accounting-software/accept-payments/tap-to-pay-android/`). This is an APAC product-behavior reference; the underlying reconcile pattern is the key inference.
- Reserve Bank of New Zealand material says cheques have been phased out in New Zealand and notes the last major bank cheque services ceased in July 2021. Sources: RBNZ 2024 joint report and RBNZ cash-and-payments update (`https://www.rbnz.govt.nz/...jointreport...pdf`, `https://www.rbnz.govt.nz/...cash-and-payments-data-update-covid-19-special.pdf`).
- Xero ecosystem batch-payment tooling is oriented to **accounts payable bills** rather than customer receipts. Source: BatchPay on the Xero App Store (`https://apps.xero.com/nz/app/batchpay`). This is supporting ecosystem evidence, not a core Xero product contract.

## Problem
The current SlowBooks workflows mix three distinct cases:
1. **Electronic receipts** that will later appear in bank feeds (EFT / EFTPOS / card).
2. **Physical cash receipts** that may need temporary clearing before a bank deposit.
3. **High-volume bulk receipt allocation**, which currently looks like a manual batch-entry screen even though the more natural system of record is often the bank feed.

This leaves uncertainty about when users should record a receipt manually, when they should wait for statement lines, and whether features like Undeposited Funds, Batch Payments, and Check Register still fit NZ practice.

## Recommended product decisions

### 1) Keep customer receipts, but split the workflow by payment type
- **EFT / bank transfer**
  - Recommended primary workflow: **bank-feed-first**. When the transfer appears in imported bank transactions, users should match/allocate it to the invoice from banking/reconciliation.
  - Keep manual “record receipt” as a secondary path for known remittances or when users receive payment advice before the bank line arrives.
  - Manual EFT receipts should default to a **bank account**, not Undeposited Funds.
- **EFTPOS / card terminal**
  - Recommended primary workflow: treat this as a **bank-settled electronic receipt**, reconciled from bank-feed lines.
  - If the settlement is 1:1 and gross, direct-to-bank is acceptable.
  - If settlements are batched or net of merchant fees, plan a later **merchant clearing** account workflow rather than abusing Undeposited Funds.
- **Cash**
  - Recommended workflow: invoice -> receive cash -> post to **Undeposited Funds / Receipt Clearing** -> later use **Make Deposits** when cash is physically banked.
  - This is the one case where the existing deposit flow still clearly fits.

### 2) Keep Undeposited Funds, but narrow its role
- Keep the system account, but treat it as **cash / receipt clearing**, not the default for ordinary electronic receipts.
- Update UI copy so users understand it is mainly for cash takings awaiting bank deposit.

### 3) Keep deposits, but narrow the UX to cash-clearing scenarios
- Retain the deposit workflow because it matches real cash-handling.
- Update wording so pending deposits are explicitly about **cash/receipt clearing**, not generic customer payments.
- Consider filtering pending deposits to receipt-clearing payments only, with method-aware cues.

### 4) Keep the register concept, but retire “Check Register” terminology
- The current feature is really an **asset-account running register**.
- Recommended cleanup: rename the UI to **Bank Register** or **Account Register**.
- Keep the underlying feature because it remains useful for bank-account history and troubleshooting, even though cheques are obsolete.

### 5) Retire or repurpose the current customer “Batch Payments” feature
- Current batch payments are a poor fit for NZ customer-receipt reality because most high-volume electronic receipts are better handled from bank feeds/reconciliation.
- Recommended direction:
  - **Short term:** hide/de-emphasize Batch Payments from the primary NZ sales workflow.
  - **Medium term:** either remove it or repurpose it to **Bulk Receipt Allocation** for exceptional remittance-style use cases.
  - Do **not** keep calling it “Batch Payments” if it remains on the sales side; that name aligns more naturally with AP bill runs.

## Viable options

### Option A — Conservative cleanup
- Remove cheque language
- Rename Check Register -> Bank Register
- Change defaults/copy so EFT/EFTPOS go to bank, cash goes to Undeposited Funds
- Keep Batch Payments but de-emphasize it

**Pros**
- Smallest change surface
- Preserves existing capability

**Cons**
- Leaves some conceptual overlap between manual receipts and bank-feed matching
- Batch Payments remains awkwardly named and positioned

### Option B — Recommended hybrid NZ model
- Keep manual customer receipts for exceptions and cash
- Make banking/reconciliation the primary path for EFT/EFTPOS receipts
- Narrow Undeposited Funds and deposits to cash-clearing
- Rename Check Register
- Repurpose or retire sales-side Batch Payments

**Pros**
- Best fit to NZ payment reality and Xero-style bank-feed-first workflows
- Cleaner mental model
- Reduces duplicate-entry pressure

**Cons**
- Requires more UX and workflow cleanup than a simple label pass
- Likely needs follow-on reconciliation improvements

### Option C — Remove manual receipt flows aggressively
- Push most receipt capture into banking only
- Keep only cash handling as a special flow

**Pros**
- Very clean conceptual model

**Cons**
- Too disruptive right now
- Risks breaking valid “payment advice before bank feed” workflows

## Recommendation
Choose **Option B**.

It preserves legitimate manual receipt use cases while aligning the default operational flow with NZ electronic payment reality and Xero-style reconciliation patterns.

## Proposed cleanup phases

### Phase 1 — Vocabulary and default cleanup
- Remove remaining cheque/check language from customer-receipt flows and related labels.
- Replace method values with NZ-relevant language: `EFT`, `EFTPOS/Card`, `Cash`, `Other`.
- Rename **Check Register** -> **Bank Register** in UI/nav.
- Update receive-payment defaults and copy:
  - cash -> Undeposited Funds / Receipt Clearing
  - EFT / EFTPOS -> direct bank account (or no explicit deposit target if bank-feed-first becomes primary)

### Phase 2 — Method-aware receipt/deposit behavior
- Make the receive-payment form explain when to use it versus waiting for the bank feed.
- Restrict/label deposit workflow as a cash-clearing function.
- Ensure pending deposits reflect receipt-clearing items only.

### Phase 3 — Reconciliation-led electronic receipt flow
- Improve banking reconciliation so imported statement lines can confidently match/allocate to invoices without needing prior manual receipt entry in common EFT/EFTPOS scenarios.
- Consider a merchant clearing account path for batched/net card settlements.

### Phase 4 — Batch Payments decision
- Remove from sales nav, or
- rename to **Bulk Receipt Allocation** and limit it to explicit remittance/import-heavy workflows.

## Acceptance criteria
1. Customer receipt workflows no longer present cheque-era mental models for NZ users.
2. Cash receipts have a clear Undeposited Funds -> deposit workflow.
3. EFT/EFTPOS guidance and defaults steer users toward bank/reconciliation-led handling.
4. Check Register is renamed to a bank/register concept without losing the running-balance utility.
5. Batch Payments is either retired from the primary sales flow or clearly repurposed.

## Risks and mitigations
- **Risk:** users still manually record EFT receipts and later duplicate them during reconciliation.  
  **Mitigation:** explicit UI guidance and reconciliation matching improvements.
- **Risk:** removing or hiding Batch Payments frustrates niche bulk-remittance users.  
  **Mitigation:** repurpose before removing, and validate actual usage.
- **Risk:** card settlements with merchant fees do not fit either direct bank or undeposited funds cleanly.  
  **Mitigation:** plan a later merchant-clearing slice rather than forcing a misleading default now.

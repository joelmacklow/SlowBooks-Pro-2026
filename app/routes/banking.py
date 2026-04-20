# ============================================================================
# Decompiled from qbw32.exe!CBankManager + CReconcileEngine
# Offset: 0x001E7200 (BankAcct) / 0x001F0400 (Reconcile)
# The reconciliation engine was CReconcileEngine::ComputeDifference() at
# 0x001F0890. Toggle cleared items, then validate sum matches statement.
# ============================================================================

from datetime import UTC, datetime
from sqlalchemy import func as sqlfunc
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.accounts import Account, AccountType
from app.models.banking import BankAccount, BankRule, BankRuleDirection, BankTransaction, Reconciliation, ReconciliationStatus
from app.models.bills import Bill, BillPayment, BillStatus
from app.models.credit_memos import CreditMemo, CreditMemoLine, CreditMemoStatus
from app.models.invoices import Invoice, InvoiceStatus
from app.models.payments import Payment
from app.models.transactions import Transaction, TransactionLine
from app.routes.bill_payments import create_bill_payment as create_bill_payment_entry
from app.routes.payments import create_payment as create_payment_entry
from app.schemas.banking import (
    BankAccountCreate, BankAccountUpdate, BankAccountResponse,
    BankTransactionCreate, BankTransactionResponse,
    ReconciliationCreate, ReconciliationResponse,
    BankTransactionMatchApproval, BankTransactionCodeApproval,
    BankTransactionRuleApproval, BankTransactionSplitCodeApproval, BankRuleCreate, BankRuleResponse, BankRuleUpdate,
)
from app.schemas.bills import BillPaymentAllocationCreate, BillPaymentCreate
from app.schemas.payments import PaymentAllocationCreate, PaymentCreate
from app.services.accounting import create_journal_entry, get_ap_account_id, get_ar_account_id
from app.services.auth import require_permissions
from app.services.bank_rules import (
    bank_rule_payload,
    bank_rule_reason_text,
    find_matching_bank_rule,
    validate_bank_rule_target_account,
)
from app.services.closing_date import check_closing_date
from app.services.reconciliation_matching import search_candidates, suggestion_candidates, transaction_direction

router = APIRouter(prefix="/api/banking", tags=["banking"])


def _bank_transaction_payload(db: Session, bank_txn: BankTransaction) -> dict:
    matched_label = None
    if bank_txn.match_status == "coded" and bank_txn.category_account:
        matched_label = f"Coded to {bank_txn.category_account.name}"
    elif bank_txn.transaction_id:
        source_type = bank_txn.transaction.source_type if bank_txn.transaction else ""
        if source_type == "payment":
            matched_label = "Matched to customer payment"
        elif source_type == "bill_payment":
            matched_label = "Matched to bill payment"
        elif source_type == "bank_transaction_split_code":
            bank_account_id = bank_txn.bank_account.account_id if bank_txn.bank_account else None
            split_count = len([
                line for line in (bank_txn.transaction.lines if bank_txn.transaction else [])
                if line.account_id != bank_account_id
            ])
            matched_label = f"Split coded across {split_count} accounts" if split_count else "Split coded"
        else:
            matched_label = "Matched transaction"

    suggestions = []
    rule_suggestion = None
    if bank_txn.transaction_id is None and bank_txn.match_status != "coded":
        suggestions = suggestion_candidates(db, bank_txn)
        matched_rule, reasons = find_matching_bank_rule(db, bank_txn)
        if matched_rule:
            rule_suggestion = bank_rule_payload(matched_rule, reasons)

    return {
        "id": bank_txn.id,
        "date": bank_txn.date.isoformat(),
        "payee": bank_txn.payee or "",
        "description": bank_txn.description or "",
        "reference": bank_txn.reference or "",
        "code": bank_txn.code or "",
        "amount": float(bank_txn.amount),
        "reconciled": bank_txn.reconciled,
        "match_status": bank_txn.match_status or "unmatched",
        "matched_label": matched_label,
        "suggestions": suggestions,
        "rule_suggestion": rule_suggestion,
    }


def _bank_rule_response(rule: BankRule) -> BankRuleResponse:
    response = BankRuleResponse.model_validate(rule)
    response.bank_account_name = rule.bank_account.name if rule.bank_account else None
    response.target_account_name = rule.target_account.name if rule.target_account else None
    return response


def _validate_bank_rule_fields(data: BankRuleCreate | BankRuleUpdate) -> None:
    if not any(
        getattr(data, field_name, None)
        for field_name in ("payee_contains", "description_contains", "reference_contains", "code_equals")
    ):
        raise HTTPException(status_code=400, detail="Provide at least one match criterion for a bank rule")


def _clean_bank_rule_data(values: dict) -> dict:
    cleaned = dict(values)
    for key in ("name", "payee_contains", "description_contains", "reference_contains", "code_equals", "default_description"):
        if key in cleaned and isinstance(cleaned[key], str):
            cleaned[key] = cleaned[key].strip() or None
    if "name" in cleaned and cleaned["name"] is None:
        raise HTTPException(status_code=400, detail="Rule name is required")
    return cleaned


def _validate_rule_bank_account(db: Session, bank_account_id: int | None) -> None:
    if bank_account_id is None:
        return
    bank_account = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.is_active == True).first()
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")


def _get_bank_transaction_or_404(db: Session, txn_id: int) -> BankTransaction:
    bank_txn = db.query(BankTransaction).filter(BankTransaction.id == txn_id).first()
    if not bank_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return bank_txn


def _linked_bank_account_or_400(db: Session, bank_txn: BankTransaction) -> BankAccount:
    bank_account = db.query(BankAccount).filter(BankAccount.id == bank_txn.bank_account_id).first()
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    if not bank_account.account_id:
        raise HTTPException(status_code=400, detail="Bank account must be linked to a chart-of-accounts asset account before matching or coding")
    return bank_account


def _assert_transaction_matchable(bank_txn: BankTransaction) -> None:
    if bank_txn.transaction_id:
        raise HTTPException(status_code=400, detail="Bank transaction is already linked to an accounting transaction")
    if bank_txn.match_status == "coded":
        raise HTTPException(status_code=400, detail="Bank transaction is already coded")


def _posting_description(bank_txn: BankTransaction, fallback: str) -> str:
    return fallback or bank_txn.description or bank_txn.payee or f"Bank statement line {bank_txn.id}"


@router.get("/rules", response_model=list[BankRuleResponse])
def list_bank_rules(db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    rules = db.query(BankRule).order_by(BankRule.priority.asc(), BankRule.id.asc()).all()
    return [_bank_rule_response(rule) for rule in rules]


@router.post("/rules", response_model=BankRuleResponse, status_code=201)
def create_bank_rule(data: BankRuleCreate, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    _validate_bank_rule_fields(data)
    _validate_rule_bank_account(db, data.bank_account_id)
    try:
        validate_bank_rule_target_account(db, data.target_account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    rule = BankRule(**_clean_bank_rule_data(data.model_dump()))
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _bank_rule_response(rule)


@router.put("/rules/{rule_id}", response_model=BankRuleResponse)
def update_bank_rule(rule_id: int, data: BankRuleUpdate, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    rule = db.query(BankRule).filter(BankRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Bank rule not found")

    updates = _clean_bank_rule_data(data.model_dump(exclude_unset=True))
    merged = {
        "payee_contains": updates.get("payee_contains", rule.payee_contains),
        "description_contains": updates.get("description_contains", rule.description_contains),
        "reference_contains": updates.get("reference_contains", rule.reference_contains),
        "code_equals": updates.get("code_equals", rule.code_equals),
    }
    if not any(merged.values()):
        raise HTTPException(status_code=400, detail="Provide at least one match criterion for a bank rule")

    bank_account_id = updates.get("bank_account_id", rule.bank_account_id)
    _validate_rule_bank_account(db, bank_account_id)
    if "target_account_id" in updates:
        try:
            validate_bank_rule_target_account(db, updates["target_account_id"])
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    for key, val in updates.items():
        setattr(rule, key, val)
    db.commit()
    db.refresh(rule)
    return _bank_rule_response(rule)


@router.delete("/rules/{rule_id}")
def delete_bank_rule(rule_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    rule = db.query(BankRule).filter(BankRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Bank rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "deleted", "rule_id": rule_id}


def _next_credit_memo_number(db: Session) -> str:
    last = db.query(sqlfunc.max(CreditMemo.memo_number)).scalar()
    if last and last.replace("CM-", "").isdigit():
        num = int(last.replace("CM-", "")) + 1
        return f"CM-{num:04d}"
    return "CM-0001"


def _create_overpayment_credit_note(db: Session, invoice: Invoice, excess_amount: Decimal, statement_reference: str | None, statement_code: str | None) -> CreditMemo:
    memo_number = _next_credit_memo_number(db)
    memo = CreditMemo(
        memo_number=memo_number,
        customer_id=invoice.customer_id,
        original_invoice_id=invoice.id,
        status=CreditMemoStatus.ISSUED,
        date=invoice.date,
        subtotal=excess_amount,
        tax_rate=Decimal("0"),
        tax_amount=Decimal("0"),
        total=excess_amount,
        amount_applied=Decimal("0"),
        balance_remaining=excess_amount,
        notes=f"Created from bank statement overpayment ({statement_reference or statement_code or f'bank-{invoice.id}'})",
        transaction_id=None,
    )
    db.add(memo)
    db.flush()
    db.add(CreditMemoLine(
        credit_memo_id=memo.id,
        item_id=None,
        description=f"Overpayment credit for invoice {invoice.invoice_number}",
        quantity=Decimal("1"),
        rate=excess_amount,
        amount=excess_amount,
        gst_code="NO_GST",
        gst_rate=Decimal("0"),
        line_order=0,
    ))
    return memo


# Bank Accounts
@router.get("/accounts", response_model=list[BankAccountResponse])
def list_bank_accounts(db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    return db.query(BankAccount).filter(BankAccount.is_active == True).order_by(BankAccount.name).all()


@router.get("/accounts/{account_id}", response_model=BankAccountResponse)
def get_bank_account(account_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    ba = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return ba


@router.post("/accounts", response_model=BankAccountResponse, status_code=201)
def create_bank_account(data: BankAccountCreate, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    ba = BankAccount(**data.model_dump())
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return ba


@router.put("/accounts/{account_id}", response_model=BankAccountResponse)
def update_bank_account(account_id: int, data: BankAccountUpdate, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    ba = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(ba, key, val)
    db.commit()
    db.refresh(ba)
    return ba


# Bank Transactions
@router.get("/transactions", response_model=list[BankTransactionResponse])
def list_bank_transactions(bank_account_id: int = None, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    q = db.query(BankTransaction)
    if bank_account_id:
        q = q.filter(BankTransaction.bank_account_id == bank_account_id)
    return q.order_by(BankTransaction.date.desc(), BankTransaction.id.desc()).all()


@router.get("/transactions/{txn_id}/suggestions")
def get_bank_transaction_suggestions(txn_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    bank_txn = _get_bank_transaction_or_404(db, txn_id)
    matched_rule, reasons = find_matching_bank_rule(db, bank_txn)
    return {
        "transaction": _bank_transaction_payload(db, bank_txn),
        "direction": transaction_direction(bank_txn),
        "suggestions": suggestion_candidates(db, bank_txn),
        "rule_suggestion": bank_rule_payload(matched_rule, reasons) if matched_rule else None,
    }


@router.get("/transactions/{txn_id}/search")
def search_bank_transaction_matches(txn_id: int, query: str = Query(default=""), db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    bank_txn = _get_bank_transaction_or_404(db, txn_id)
    return {
        "direction": transaction_direction(bank_txn),
        "query": query,
        "candidates": search_candidates(db, bank_txn, query=query),
    }


@router.post("/transactions", response_model=BankTransactionResponse, status_code=201)
def create_bank_transaction(data: BankTransactionCreate, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    check_closing_date(db, data.date)
    ba = db.query(BankAccount).filter(BankAccount.id == data.bank_account_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")

    txn = BankTransaction(**data.model_dump(), match_status="unmatched")
    ba.balance = Decimal(str(ba.balance or 0)) + Decimal(str(data.amount))
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.post("/transactions/{txn_id}/approve-match")
def approve_bank_transaction_match(txn_id: int, data: BankTransactionMatchApproval, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    bank_txn = _get_bank_transaction_or_404(db, txn_id)
    _assert_transaction_matchable(bank_txn)
    bank_account = _linked_bank_account_or_400(db, bank_txn)

    amount = Decimal(str(bank_txn.amount or 0))
    if data.match_kind == "invoice":
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Only payment-in statement lines can be matched to invoices")
        invoice = db.query(Invoice).filter(Invoice.id == data.target_id).first()
        if not invoice or invoice.status not in (InvoiceStatus.SENT, InvoiceStatus.PARTIAL):
            raise HTTPException(status_code=404, detail="Outstanding invoice not found")
        invoice_balance = Decimal(str(invoice.balance_due or 0))
        allocation_amount = min(invoice_balance, amount)
        excess_amount = amount - allocation_amount

        created = create_payment_entry(
            PaymentCreate(
                customer_id=invoice.customer_id,
                date=bank_txn.date,
                amount=amount,
                method="EFT",
                check_number=None,
                reference=bank_txn.reference or bank_txn.code or f"bank-{bank_txn.id}",
                deposit_to_account_id=bank_account.account_id,
                notes=f"Matched from bank statement line {bank_txn.id}",
                allocations=[PaymentAllocationCreate(invoice_id=invoice.id, amount=allocation_amount)],
            ),
            db=db,
            auth=True,
        )
        payment = db.query(Payment).filter(Payment.id == created.id).first()
        credit_memo = None
        if excess_amount > Decimal("0.01"):
            credit_memo = _create_overpayment_credit_note(db, invoice, excess_amount, bank_txn.reference, bank_txn.code)
        bank_txn.transaction_id = payment.transaction_id if payment else None
        bank_txn.category_account_id = get_ar_account_id(db)
        bank_txn.match_status = "manual"
        bank_txn.reconciled = True
        db.commit()
        matched_label = f"Invoice {invoice.invoice_number}"
        if credit_memo:
            matched_label = f"Invoice {invoice.invoice_number} + Credit Note {credit_memo.memo_number}"
        return {"status": "matched", "transaction_id": bank_txn.id, "matched_label": matched_label}

    if data.match_kind == "bill":
        if amount >= 0:
            raise HTTPException(status_code=400, detail="Only payment-out statement lines can be matched to bills")
        bill = db.query(Bill).filter(Bill.id == data.target_id).first()
        if not bill or bill.status not in (BillStatus.UNPAID, BillStatus.PARTIAL):
            raise HTTPException(status_code=404, detail="Outstanding bill not found")
        payment_amount = abs(amount)
        if Decimal(str(bill.balance_due or 0)) < payment_amount:
            raise HTTPException(status_code=400, detail="Statement amount exceeds bill balance")

        created = create_bill_payment_entry(
            BillPaymentCreate(
                vendor_id=bill.vendor_id,
                date=bank_txn.date,
                amount=float(payment_amount),
                method="EFT",
                check_number=bank_txn.reference or bank_txn.code or f"bank-{bank_txn.id}",
                pay_from_account_id=bank_account.account_id,
                notes=f"Matched from bank statement line {bank_txn.id}",
                allocations=[BillPaymentAllocationCreate(bill_id=bill.id, amount=float(payment_amount))],
            ),
            db=db,
            auth=True,
        )
        payment = db.query(BillPayment).filter(BillPayment.id == created.id).first()
        bank_txn.transaction_id = payment.transaction_id if payment else None
        bank_txn.category_account_id = get_ap_account_id(db)
        bank_txn.match_status = "manual"
        bank_txn.reconciled = True
        db.commit()
        return {"status": "matched", "transaction_id": bank_txn.id, "matched_label": f"Bill {bill.bill_number}"}

    raise HTTPException(status_code=400, detail="Unsupported match kind")


@router.post("/transactions/{txn_id}/code")
def code_bank_transaction(txn_id: int, data: BankTransactionCodeApproval, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    bank_txn = _get_bank_transaction_or_404(db, txn_id)
    _assert_transaction_matchable(bank_txn)
    bank_account = _linked_bank_account_or_400(db, bank_txn)
    target_account = db.query(Account).filter(Account.id == data.account_id, Account.is_active == True).first()
    if not target_account:
        raise HTTPException(status_code=404, detail="Account not found")
    if target_account.id == bank_account.account_id:
        raise HTTPException(status_code=400, detail="Choose a different account from the linked bank account")

    check_closing_date(db, bank_txn.date)
    amount = Decimal(str(bank_txn.amount or 0))
    absolute_amount = abs(amount)
    description = _posting_description(bank_txn, data.description)

    if amount >= 0:
        journal_lines = [
            {"account_id": bank_account.account_id, "debit": absolute_amount, "credit": Decimal("0"), "description": description},
            {"account_id": target_account.id, "debit": Decimal("0"), "credit": absolute_amount, "description": description},
        ]
    else:
        journal_lines = [
            {"account_id": target_account.id, "debit": absolute_amount, "credit": Decimal("0"), "description": description},
            {"account_id": bank_account.account_id, "debit": Decimal("0"), "credit": absolute_amount, "description": description},
        ]

    txn = create_journal_entry(
        db,
        bank_txn.date,
        description,
        journal_lines,
        source_type="bank_transaction_code",
        source_id=bank_txn.id,
        reference=bank_txn.reference or bank_txn.code or str(bank_txn.id),
    )
    bank_txn.transaction_id = txn.id
    bank_txn.category_account_id = target_account.id
    bank_txn.match_status = "coded"
    bank_txn.reconciled = True
    bank_txn.suggested_rule_id = None
    bank_txn.suggested_account_id = None
    bank_txn.rule_match_reason = None
    db.commit()
    return {"status": "coded", "transaction_id": bank_txn.id, "matched_label": f"Coded to {target_account.name}"}


@router.post("/transactions/{txn_id}/code-split")
def split_code_bank_transaction(txn_id: int, data: BankTransactionSplitCodeApproval, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    bank_txn = _get_bank_transaction_or_404(db, txn_id)
    _assert_transaction_matchable(bank_txn)
    bank_account = _linked_bank_account_or_400(db, bank_txn)
    check_closing_date(db, bank_txn.date)

    splits = [split for split in data.splits if Decimal(str(split.amount or 0)) > 0]
    if len(splits) < 2:
        raise HTTPException(status_code=400, detail="Split coding requires at least two split lines")

    amount = Decimal(str(bank_txn.amount or 0))
    absolute_amount = abs(amount)
    split_total = sum((Decimal(str(split.amount)) for split in splits), Decimal("0.00"))
    if abs(split_total - absolute_amount) > Decimal("0.01"):
        raise HTTPException(status_code=400, detail="Split lines must total the statement amount exactly")

    journal_lines = []
    for split in splits:
        target_account = db.query(Account).filter(Account.id == split.account_id, Account.is_active == True).first()
        if not target_account:
            raise HTTPException(status_code=404, detail="Split account not found")
        if target_account.id == bank_account.account_id:
            raise HTTPException(status_code=400, detail="Split lines cannot target the linked bank account")
        split_amount = Decimal(str(split.amount))
        description = _posting_description(bank_txn, split.description)
        if amount >= 0:
            journal_lines.append({
                "account_id": target_account.id,
                "debit": Decimal("0"),
                "credit": split_amount,
                "description": description,
            })
        else:
            journal_lines.append({
                "account_id": target_account.id,
                "debit": split_amount,
                "credit": Decimal("0"),
                "description": description,
            })

    bank_description = _posting_description(bank_txn, None)
    if amount >= 0:
        journal_lines.insert(0, {
            "account_id": bank_account.account_id,
            "debit": absolute_amount,
            "credit": Decimal("0"),
            "description": bank_description,
        })
    else:
        journal_lines.append({
            "account_id": bank_account.account_id,
            "debit": Decimal("0"),
            "credit": absolute_amount,
            "description": bank_description,
        })

    txn = create_journal_entry(
        db,
        bank_txn.date,
        bank_description,
        journal_lines,
        source_type="bank_transaction_split_code",
        source_id=bank_txn.id,
        reference=bank_txn.reference or bank_txn.code or str(bank_txn.id),
    )
    bank_txn.transaction_id = txn.id
    bank_txn.category_account_id = None
    bank_txn.match_status = "coded"
    bank_txn.reconciled = True
    bank_txn.suggested_rule_id = None
    bank_txn.suggested_account_id = None
    bank_txn.rule_match_reason = None
    db.commit()
    return {"status": "coded", "transaction_id": bank_txn.id, "matched_label": f"Split coded across {len(splits)} accounts"}


@router.post("/transactions/{txn_id}/apply-rule")
def apply_bank_transaction_rule(txn_id: int, data: BankTransactionRuleApproval, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    bank_txn = _get_bank_transaction_or_404(db, txn_id)
    _assert_transaction_matchable(bank_txn)

    rule = None
    if data.rule_id is not None:
        rule = db.query(BankRule).filter(BankRule.id == data.rule_id, BankRule.is_active == True).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Bank rule not found")
    else:
        rule, _reasons = find_matching_bank_rule(db, bank_txn)
    if not rule:
        raise HTTPException(status_code=400, detail="No applicable bank rule found for this transaction")

    if rule.bank_account_id and rule.bank_account_id != bank_txn.bank_account_id:
        raise HTTPException(status_code=400, detail="Bank rule does not apply to this bank account")
    direction = transaction_direction(bank_txn)
    if rule.direction == BankRuleDirection.INFLOW and direction != "inflow":
        raise HTTPException(status_code=400, detail="Bank rule direction does not match this transaction")
    if rule.direction == BankRuleDirection.OUTFLOW and direction != "outflow":
        raise HTTPException(status_code=400, detail="Bank rule direction does not match this transaction")

    description = rule.default_description or bank_txn.description or bank_txn.payee or f"Bank rule {rule.name}"
    _matched_rule, reasons = find_matching_bank_rule(db, bank_txn)
    rule_reason = bank_rule_reason_text(reasons) if _matched_rule and _matched_rule.id == rule.id else bank_txn.rule_match_reason

    result = code_bank_transaction(
        txn_id,
        BankTransactionCodeApproval(account_id=rule.target_account_id, description=description),
        db=db,
        auth=True,
    )
    bank_txn = _get_bank_transaction_or_404(db, txn_id)
    bank_txn.suggested_rule_id = rule.id
    bank_txn.suggested_account_id = rule.target_account_id
    bank_txn.rule_match_reason = rule_reason
    db.commit()
    return {**result, "rule_id": rule.id, "matched_label": f"Applied rule {rule.name}"}


# Reconciliations — CReconcileEngine @ 0x001F0400
@router.get("/reconciliations", response_model=list[ReconciliationResponse])
def list_reconciliations(bank_account_id: int = None, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    q = db.query(Reconciliation)
    if bank_account_id:
        q = q.filter(Reconciliation.bank_account_id == bank_account_id)
    return q.order_by(Reconciliation.statement_date.desc()).all()


@router.post("/reconciliations", response_model=ReconciliationResponse, status_code=201)
def create_reconciliation(data: ReconciliationCreate, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    ba = db.query(BankAccount).filter(BankAccount.id == data.bank_account_id).first()
    if not ba:
        raise HTTPException(status_code=404, detail="Bank account not found")
    if data.import_batch_id:
        existing = db.query(Reconciliation).filter(
            Reconciliation.bank_account_id == data.bank_account_id,
            Reconciliation.import_batch_id == data.import_batch_id,
            Reconciliation.status == ReconciliationStatus.IN_PROGRESS,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="A reconciliation already exists for this import batch")
    recon = Reconciliation(**data.model_dump())
    db.add(recon)
    db.commit()
    db.refresh(recon)
    return recon


@router.post("/reconciliations/{recon_id}/cancel")
def cancel_reconciliation(recon_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    recon = db.query(Reconciliation).filter(Reconciliation.id == recon_id).first()
    if not recon:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    if recon.status == ReconciliationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Completed reconciliations cannot be cancelled")
    if not recon.import_batch_id:
        db.delete(recon)
        db.commit()
        return {"status": "cancelled", "reconciliation_id": recon_id, "removed_transactions": 0}

    txns = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id == recon.bank_account_id,
        BankTransaction.import_batch_id == recon.import_batch_id,
    ).all()
    touched = [
        txn for txn in txns
        if txn.reconciled or txn.transaction_id or txn.match_status in ("coded", "manual")
    ]
    if touched:
        raise HTTPException(status_code=400, detail="Cannot cancel reconciliation after matching or coding has started")

    removed_count = len(txns)
    for txn in txns:
        db.delete(txn)
    db.delete(recon)
    db.commit()
    return {"status": "cancelled", "reconciliation_id": recon_id, "removed_transactions": removed_count}


@router.get("/reconciliations/{recon_id}/transactions")
def get_reconciliation_transactions(recon_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    recon = db.query(Reconciliation).filter(Reconciliation.id == recon_id).first()
    if not recon:
        raise HTTPException(status_code=404, detail="Reconciliation not found")

    q = db.query(BankTransaction).filter(BankTransaction.bank_account_id == recon.bank_account_id)
    if recon.import_batch_id:
        q = q.filter(BankTransaction.import_batch_id == recon.import_batch_id)
    else:
        q = q.filter(BankTransaction.date <= recon.statement_date)
    txns = q.order_by(BankTransaction.date, BankTransaction.id).all()

    cleared_total = sum(float(t.amount) for t in txns if t.reconciled)
    uncleared_total = sum(float(t.amount) for t in txns if not t.reconciled)
    statement_bal = float(recon.statement_balance)
    difference = statement_bal - cleared_total

    return {
        "reconciliation_id": recon.id,
        "statement_balance": statement_bal,
        "statement_label": "Transactions to clear" if recon.import_batch_id else "Statement Balance",
        "cleared_total": cleared_total,
        "uncleared_total": uncleared_total,
        "difference": difference,
        "import_batch_id": recon.import_batch_id,
        "transactions": [_bank_transaction_payload(db, txn) for txn in txns],
    }


@router.post("/reconciliations/{recon_id}/toggle/{txn_id}")
def toggle_cleared(recon_id: int, txn_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    recon = db.query(Reconciliation).filter(Reconciliation.id == recon_id).first()
    if not recon:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    if recon.status == ReconciliationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Reconciliation already completed")

    txn = db.query(BankTransaction).filter(BankTransaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.reconciled = not txn.reconciled
    db.commit()
    return {"id": txn.id, "reconciled": txn.reconciled}


@router.get("/check-register")
def check_register(account_id: int = None, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    if not account_id:
        account = db.query(Account).filter(Account.account_type == AccountType.ASSET, Account.is_active == True).order_by(Account.account_number, Account.name).first()
    else:
        account = db.query(Account).filter(Account.id == account_id, Account.is_active == True).first()
    if not account:
        return {"account_id": None, "account_name": "", "account_number": "", "starting_balance": 0, "entries": []}
    if account.account_type != AccountType.ASSET:
        raise HTTPException(status_code=400, detail="Check register requires an asset account")

    rows = (
        db.query(TransactionLine, Transaction)
        .join(Transaction, TransactionLine.transaction_id == Transaction.id)
        .filter(TransactionLine.account_id == account.id)
        .order_by(Transaction.date.asc(), Transaction.id.asc(), TransactionLine.id.asc())
        .all()
    )

    total_effect = sum(Decimal(str(line.debit)) - Decimal(str(line.credit)) for line, _txn in rows)
    running_balance = Decimal(str(account.balance or 0)) - total_effect
    starting_balance = running_balance
    entries = []
    for line, txn in rows:
        running_balance += Decimal(str(line.debit)) - Decimal(str(line.credit))
        entries.append({
            "transaction_id": txn.id,
            "date": txn.date.isoformat(),
            "description": txn.description or line.description or "",
            "reference": txn.reference or "",
            "source_type": txn.source_type or "",
            "payment": float(line.credit) if Decimal(str(line.credit)) > 0 else 0,
            "deposit": float(line.debit) if Decimal(str(line.debit)) > 0 else 0,
            "balance": float(running_balance),
        })

    return {
        "account_id": account.id,
        "account_name": account.name,
        "account_number": account.account_number,
        "starting_balance": float(starting_balance),
        "entries": entries,
    }


@router.post("/reconciliations/{recon_id}/complete")
def complete_reconciliation(recon_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.manage"))):
    recon = db.query(Reconciliation).filter(Reconciliation.id == recon_id).first()
    if not recon:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    if recon.status == ReconciliationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Already completed")

    q = db.query(BankTransaction).filter(BankTransaction.bank_account_id == recon.bank_account_id)
    if recon.import_batch_id:
        q = q.filter(BankTransaction.import_batch_id == recon.import_batch_id)
    else:
        q = q.filter(BankTransaction.date <= recon.statement_date)
    txns = q.filter(BankTransaction.reconciled == True).all()
    cleared_total = sum(t.amount for t in txns)

    if abs(cleared_total - recon.statement_balance) > Decimal("0.01"):
        raise HTTPException(
            status_code=400,
            detail=f"Difference is ${float(recon.statement_balance - cleared_total):.2f} — must be $0.00 to complete",
        )

    if recon.import_batch_id:
        existing_applied = db.query(Reconciliation).filter(
            Reconciliation.bank_account_id == recon.bank_account_id,
            Reconciliation.import_batch_id == recon.import_batch_id,
            Reconciliation.balance_applied_at.isnot(None),
            Reconciliation.id != recon.id,
        ).first()
        if existing_applied:
            raise HTTPException(status_code=400, detail="This import batch has already been applied to the bank account balance")

        if recon.balance_applied_at is None:
            bank_account = db.query(BankAccount).filter(BankAccount.id == recon.bank_account_id).first()
            if not bank_account:
                raise HTTPException(status_code=404, detail="Bank account not found")
            bank_account.balance = Decimal(str(bank_account.balance or 0)) + Decimal(str(recon.statement_balance))
            recon.balance_applied_at = datetime.now(UTC)

    recon.status = ReconciliationStatus.COMPLETED
    recon.completed_at = datetime.now(UTC)
    db.commit()
    return {"status": "completed", "reconciliation_id": recon.id}

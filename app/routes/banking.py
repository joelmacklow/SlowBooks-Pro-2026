# ============================================================================
# Decompiled from qbw32.exe!CBankManager + CReconcileEngine
# Offset: 0x001E7200 (BankAcct) / 0x001F0400 (Reconcile)
# The reconciliation engine was CReconcileEngine::ComputeDifference() at
# 0x001F0890. Toggle cleared items, then validate sum matches statement.
# ============================================================================

from datetime import datetime
from sqlalchemy import func as sqlfunc
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.accounts import Account, AccountType
from app.models.banking import BankAccount, BankTransaction, Reconciliation, ReconciliationStatus
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
)
from app.schemas.bills import BillPaymentAllocationCreate, BillPaymentCreate
from app.schemas.payments import PaymentAllocationCreate, PaymentCreate
from app.services.accounting import create_journal_entry, get_ap_account_id, get_ar_account_id
from app.services.auth import require_permissions
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
        else:
            matched_label = "Matched transaction"

    suggestions = []
    if bank_txn.transaction_id is None and bank_txn.match_status != "coded":
        suggestions = suggestion_candidates(db, bank_txn)

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
    }


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
    return {
        "transaction": _bank_transaction_payload(db, bank_txn),
        "direction": transaction_direction(bank_txn),
        "suggestions": suggestion_candidates(db, bank_txn),
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
    description = data.description or bank_txn.description or bank_txn.payee or f"Bank statement line {bank_txn.id}"

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
    db.commit()
    return {"status": "coded", "transaction_id": bank_txn.id, "matched_label": f"Coded to {target_account.name}"}


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
    recon = Reconciliation(**data.model_dump())
    db.add(recon)
    db.commit()
    db.refresh(recon)
    return recon


@router.get("/reconciliations/{recon_id}/transactions")
def get_reconciliation_transactions(recon_id: int, db: Session = Depends(get_db), auth=Depends(require_permissions("banking.view"))):
    recon = db.query(Reconciliation).filter(Reconciliation.id == recon_id).first()
    if not recon:
        raise HTTPException(status_code=404, detail="Reconciliation not found")

    txns = (
        db.query(BankTransaction)
        .filter(BankTransaction.bank_account_id == recon.bank_account_id)
        .filter(BankTransaction.date <= recon.statement_date)
        .order_by(BankTransaction.date, BankTransaction.id)
        .all()
    )

    cleared_total = sum(float(t.amount) for t in txns if t.reconciled)
    uncleared_total = sum(float(t.amount) for t in txns if not t.reconciled)
    statement_bal = float(recon.statement_balance)
    difference = statement_bal - cleared_total

    return {
        "reconciliation_id": recon.id,
        "statement_balance": statement_bal,
        "cleared_total": cleared_total,
        "uncleared_total": uncleared_total,
        "difference": difference,
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

    txns = (
        db.query(BankTransaction)
        .filter(BankTransaction.bank_account_id == recon.bank_account_id)
        .filter(BankTransaction.date <= recon.statement_date)
        .filter(BankTransaction.reconciled == True)
        .all()
    )
    cleared_total = sum(t.amount for t in txns)

    if abs(cleared_total - recon.statement_balance) > Decimal("0.01"):
        raise HTTPException(
            status_code=400,
            detail=f"Difference is ${float(recon.statement_balance - cleared_total):.2f} — must be $0.00 to complete",
        )

    recon.status = ReconciliationStatus.COMPLETED
    recon.completed_at = datetime.utcnow()
    db.commit()
    return {"status": "completed", "reconciliation_id": recon.id}

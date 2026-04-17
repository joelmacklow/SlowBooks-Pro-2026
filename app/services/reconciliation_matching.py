from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.bills import Bill, BillStatus
from app.models.banking import BankTransaction
from app.models.contacts import Customer, Vendor
from app.models.invoices import Invoice, InvoiceStatus


def transaction_direction(bank_txn: BankTransaction) -> str:
    return "inflow" if Decimal(str(bank_txn.amount or 0)) >= 0 else "outflow"


def suggestion_candidates(db: Session, bank_txn: BankTransaction, limit: int = 5) -> list[dict]:
    direction = transaction_direction(bank_txn)
    if direction == "inflow":
        candidates = _invoice_candidates(db, bank_txn)
    else:
        candidates = _bill_candidates(db, bank_txn)
    filtered = [candidate for candidate in candidates if candidate["score"] > 0]
    return sorted(filtered, key=lambda candidate: (-candidate["score"], candidate["label"]))[:limit]


def search_candidates(db: Session, bank_txn: BankTransaction, query: str = "", limit: int = 20) -> list[dict]:
    direction = transaction_direction(bank_txn)
    if direction == "inflow":
        return _invoice_candidates(db, bank_txn, query=query, limit=limit)
    return _bill_candidates(db, bank_txn, query=query, limit=limit)


def _invoice_candidates(db: Session, bank_txn: BankTransaction, query: str = "", limit: int = 20) -> list[dict]:
    amount = Decimal(str(bank_txn.amount or 0))
    if amount <= 0:
        return []

    q = db.query(Invoice).join(Customer, Invoice.customer_id == Customer.id)
    q = q.filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]))
    q = q.filter(Invoice.balance_due > 0)
    if query:
        pattern = f"%{query}%"
        q = q.filter(or_(Invoice.invoice_number.ilike(pattern), Customer.name.ilike(pattern)))
    invoices = q.order_by(Invoice.date.desc(), Invoice.id.desc()).limit(limit * 3).all()
    candidates = [_invoice_candidate(bank_txn, invoice) for invoice in invoices]
    return sorted(candidates, key=lambda candidate: (-candidate["score"], candidate["label"]))[:limit]


def _bill_candidates(db: Session, bank_txn: BankTransaction, query: str = "", limit: int = 20) -> list[dict]:
    amount = abs(Decimal(str(bank_txn.amount or 0)))
    if amount <= 0:
        return []

    q = db.query(Bill).join(Vendor, Bill.vendor_id == Vendor.id)
    q = q.filter(Bill.status.in_([BillStatus.UNPAID, BillStatus.PARTIAL]))
    q = q.filter(Bill.balance_due > 0)
    if query:
        pattern = f"%{query}%"
        q = q.filter(or_(Bill.bill_number.ilike(pattern), Vendor.name.ilike(pattern), Bill.ref_number.ilike(pattern)))
    bills = q.order_by(Bill.date.desc(), Bill.id.desc()).limit(limit * 3).all()
    candidates = [_bill_candidate(bank_txn, bill) for bill in bills]
    return sorted(candidates, key=lambda candidate: (-candidate["score"], candidate["label"]))[:limit]


def _invoice_candidate(bank_txn: BankTransaction, invoice: Invoice) -> dict:
    party_name = invoice.customer.name if invoice.customer else ""
    doc_number = invoice.invoice_number or ""
    balance = Decimal(str(invoice.balance_due or 0))
    score, reasons = _score_candidate(
        bank_txn,
        balance,
        doc_number,
        party_name,
        extra_text=[getattr(invoice, "terms", "")],
        candidate_date=invoice.date,
    )
    return {
        "kind": "invoice",
        "target_id": invoice.id,
        "label": f"Invoice {doc_number} · {party_name}",
        "document_number": doc_number,
        "party_name": party_name,
        "open_amount": float(balance),
        "date": invoice.date.isoformat() if invoice.date else "",
        "score": score,
        "reasons": reasons,
    }


def _bill_candidate(bank_txn: BankTransaction, bill: Bill) -> dict:
    party_name = bill.vendor.name if bill.vendor else ""
    doc_number = bill.bill_number or ""
    balance = Decimal(str(bill.balance_due or 0))
    score, reasons = _score_candidate(
        bank_txn,
        balance,
        doc_number,
        party_name,
        extra_text=[bill.ref_number or ""],
        candidate_date=bill.date,
    )
    return {
        "kind": "bill",
        "target_id": bill.id,
        "label": f"Bill {doc_number} · {party_name}",
        "document_number": doc_number,
        "party_name": party_name,
        "open_amount": float(balance),
        "date": bill.date.isoformat() if bill.date else "",
        "score": score,
        "reasons": reasons,
    }


def _score_candidate(bank_txn: BankTransaction, open_amount: Decimal, document_number: str, party_name: str, extra_text: list[str] | None = None, candidate_date: date | None = None) -> tuple[int, list[str]]:
    amount = abs(Decimal(str(bank_txn.amount or 0)))
    score = 0
    reasons: list[str] = []
    ref_text = " ".join(filter(None, [bank_txn.reference, bank_txn.code, bank_txn.payee, bank_txn.description]))
    ref_tokens = _tokenize(ref_text)
    number_tokens = _tokenize(document_number)
    party_tokens = _tokenize(party_name)
    extra_tokens = _tokenize(" ".join(extra_text or []))

    if abs(open_amount - amount) <= Decimal("0.01"):
        score += 55
        reasons.append("exact amount")
    elif amount < open_amount and amount > 0:
        score += 20
        reasons.append("partial amount fits")
    else:
        score -= 50

    if number_tokens & ref_tokens:
        score += 35
        reasons.append("reference/number match")
    if party_tokens & ref_tokens:
        score += 20
        reasons.append("payee name match")
    if extra_tokens & ref_tokens:
        score += 10
        reasons.append("code/reference token match")

    candidate_date_value = candidate_date
    txn_date = bank_txn.date
    if candidate_date_value and txn_date:
        day_gap = abs((txn_date - candidate_date_value).days)
        if day_gap <= 7:
            score += 8
            reasons.append("close date")
        elif day_gap <= 30:
            score += 4
            reasons.append("same month")

    if not reasons and abs(open_amount - amount) <= Decimal("1.00"):
        reasons.append("similar amount")

    return score, reasons


def _tokenize(value: str) -> set[str]:
    if not value:
        return set()
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", value.lower())
    return {token for token in normalized.split() if token}

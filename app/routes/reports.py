# ============================================================================
# Decompiled from qbw32.exe!CReportEngine  Offset: 0x00210000
# The original report engine had its own query language ("QBReportQuery")
# compiled to Btrieve API calls. The P&L report alone generated 14 separate
# Btrieve operations. We just use SQL because it's not the stone age.
# Sales Tax report was added in R3 service pack (0x002108A0).
# General Ledger was CReportEngine::RunGLDetail() at 0x00211400.
# ============================================================================

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from starlette.requests import Request

from app.database import get_db
from app.models.accounts import Account, AccountType
from app.models.banking import BankTransaction
from app.models.gst_return import GstReturn, GstReturnStatus
from app.models.gst_settlement import GstSettlement, GstSettlementStatus
from app.models.transactions import Transaction, TransactionLine
from app.models.invoices import Invoice, InvoiceStatus
from app.models.payments import Payment
from app.models.contacts import Customer
from app.schemas.email import StatementEmailRequest
from pydantic import BaseModel
from app.services.email_service import render_document_email, send_document_email
from app.services.pdf_service import generate_statement_pdf
from app.routes.settings import _get_all as get_settings
from app.services.auth import require_permissions
from app.services.rate_limit import enforce_rate_limit
from app.services.gst_return import (
    calculate_gst_return,
    generate_gst101a_pdf,
    gst_due_date,
    gst_financial_year_label,
    gst_financial_year_start,
    gst_period_windows,
)
from app.services.gst_return_filing import (
    build_confirmed_return_report,
    build_return_confirmation_state,
    confirm_return as confirm_gst_return_record,
    get_confirmed_return,
)
from app.services.gst_settlement import build_settlement_state, confirm_settlement

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _decimal_query_value(value, default=Decimal("0.00")) -> Decimal:
    if hasattr(value, "default"):
        value = value.default
    if value is None:
        return default
    return Decimal(str(value))


def _optional_query_value(value):
    if hasattr(value, "default"):
        value = value.default
    return value


def _decimal_text(value) -> str:
    return f"{Decimal(str(value or 0)).quantize(Decimal('0.00'))}"


def _period_label(start_date: date, end_date: date) -> str:
    return f"{start_date.day} {start_date.strftime('%b %Y')} - {end_date.day} {end_date.strftime('%b %Y')}"


def _draft_return_confirmation_state(start_date: date, end_date: date, box9_adjustments: Decimal, box13_adjustments: Decimal) -> dict:
    state = build_return_confirmation_state(None)
    state["due_date"] = gst_due_date(end_date).isoformat()
    state["box9_adjustments"] = _decimal_text(box9_adjustments)
    state["box13_adjustments"] = _decimal_text(box13_adjustments)
    return state


def _load_gst_return_report(db: Session, start_date: date, end_date: date, box9_adjustments: Decimal, box13_adjustments: Decimal) -> tuple[dict, GstReturn | None]:
    confirmed_return = get_confirmed_return(db, start_date, end_date)
    if confirmed_return:
        report = build_confirmed_return_report(confirmed_return)
        report["return_confirmation"] = build_return_confirmation_state(confirmed_return)
        return report, confirmed_return

    report = calculate_gst_return(
        db,
        start_date,
        end_date,
        box9_adjustments=_decimal_query_value(box9_adjustments),
        box13_adjustments=_decimal_query_value(box13_adjustments),
        include_items=False,
    )
    report["return_confirmation"] = _draft_return_confirmation_state(
        start_date,
        end_date,
        _decimal_query_value(box9_adjustments),
        _decimal_query_value(box13_adjustments),
    )
    return report, None


def _load_gst_transaction_report(db: Session, start_date: date, end_date: date, box9_adjustments: Decimal, box13_adjustments: Decimal) -> tuple[dict, GstReturn | None]:
    confirmed_return = get_confirmed_return(db, start_date, end_date)
    if confirmed_return:
        box9_adjustments = Decimal(str(confirmed_return.box9_adjustments))
        box13_adjustments = Decimal(str(confirmed_return.box13_adjustments))

    report = calculate_gst_return(
        db,
        start_date,
        end_date,
        box9_adjustments=_decimal_query_value(box9_adjustments),
        box13_adjustments=_decimal_query_value(box13_adjustments),
        include_items=True,
    )
    report["return_confirmation"] = (
        build_return_confirmation_state(confirmed_return)
        if confirmed_return else
        _draft_return_confirmation_state(start_date, end_date, _decimal_query_value(box9_adjustments), _decimal_query_value(box13_adjustments))
    )
    return report, confirmed_return


def _historical_return_from_confirmed(record: GstReturn) -> dict:
    return {
        "gst_return_id": record.id,
        "start_date": record.start_date.isoformat(),
        "end_date": record.end_date.isoformat(),
        "period_label": _period_label(record.start_date, record.end_date),
        "due_date": record.due_date.isoformat(),
        "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
        "status": "confirmed",
        "status_label": "Confirmed",
        "net_gst": float(record.net_gst),
        "net_position": record.net_position,
        "box9_adjustments": _decimal_text(record.box9_adjustments),
        "box13_adjustments": _decimal_text(record.box13_adjustments),
    }


def _historical_return_from_legacy_settlement(settlement: GstSettlement) -> dict:
    return {
        "settlement_id": settlement.id,
        "start_date": settlement.start_date.isoformat(),
        "end_date": settlement.end_date.isoformat(),
        "period_label": _period_label(settlement.start_date, settlement.end_date),
        "due_date": gst_due_date(settlement.end_date).isoformat(),
        "settlement_date": settlement.settlement_date.isoformat(),
        "status": "confirmed",
        "status_label": "Confirmed",
        "net_gst": float(settlement.net_gst),
        "net_position": settlement.net_position,
        "box9_adjustments": _decimal_text(settlement.box9_adjustments),
        "box13_adjustments": _decimal_text(settlement.box13_adjustments),
    }


@router.get("/profit-loss")
def profit_loss(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()

    def get_account_totals(acct_type):
        results = (
            db.query(Account.name, Account.account_number,
                     sqlfunc.coalesce(sqlfunc.sum(TransactionLine.credit - TransactionLine.debit), 0))
            .join(TransactionLine, TransactionLine.account_id == Account.id)
            .join(Transaction, TransactionLine.transaction_id == Transaction.id)
            .filter(Account.account_type == acct_type)
            .filter(Transaction.date >= start_date)
            .filter(Transaction.date <= end_date)
            .group_by(Account.id, Account.name, Account.account_number)
            .all()
        )
        return [{"account_name": r[0], "account_number": r[1], "amount": float(r[2])} for r in results]

    income = get_account_totals(AccountType.INCOME)
    cogs = get_account_totals(AccountType.COGS)
    expenses = get_account_totals(AccountType.EXPENSE)

    total_income = sum(i["amount"] for i in income)
    total_cogs = sum(abs(c["amount"]) for c in cogs)
    total_expenses = sum(abs(e["amount"]) for e in expenses)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "income": income,
        "cogs": cogs,
        "expenses": expenses,
        "total_income": total_income,
        "total_cogs": total_cogs,
        "gross_profit": total_income - total_cogs,
        "total_expenses": total_expenses,
        "net_income": total_income - total_cogs - total_expenses,
    }


@router.get("/balance-sheet")
def balance_sheet(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    if not as_of_date:
        as_of_date = date.today()

    def get_balances(acct_type):
        results = (
            db.query(Account.name, Account.account_number,
                     sqlfunc.coalesce(sqlfunc.sum(TransactionLine.debit - TransactionLine.credit), 0))
            .join(TransactionLine, TransactionLine.account_id == Account.id)
            .join(Transaction, TransactionLine.transaction_id == Transaction.id)
            .filter(Account.account_type == acct_type)
            .filter(Transaction.date <= as_of_date)
            .group_by(Account.id, Account.name, Account.account_number)
            .all()
        )
        return [{"account_name": r[0], "account_number": r[1], "amount": float(r[2])} for r in results]

    assets = get_balances(AccountType.ASSET)
    liabilities = get_balances(AccountType.LIABILITY)
    equity = get_balances(AccountType.EQUITY)

    total_assets = sum(a["amount"] for a in assets)
    total_liabilities = sum(abs(l["amount"]) for l in liabilities)
    total_equity = sum(abs(e["amount"]) for e in equity)

    return {
        "as_of_date": as_of_date.isoformat(),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
    }


@router.get("/ar-aging")
def ar_aging(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    if not as_of_date:
        as_of_date = date.today()

    invoices = (
        db.query(Invoice)
        .filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]))
        .filter(Invoice.date <= as_of_date)
        .filter(Invoice.balance_due > 0)
        .all()
    )

    aging = {}
    for inv in invoices:
        cid = inv.customer_id
        if cid not in aging:
            cname = db.query(Customer.name).filter(Customer.id == cid).scalar() or "Unknown"
            aging[cid] = {
                "customer_name": cname, "customer_id": cid,
                "current": Decimal(0), "over_30": Decimal(0),
                "over_60": Decimal(0), "over_90": Decimal(0), "total": Decimal(0),
            }

        days = (as_of_date - inv.due_date).days if inv.due_date else 0
        bal = inv.balance_due
        if days <= 0:
            aging[cid]["current"] += bal
        elif days <= 30:
            aging[cid]["over_30"] += bal
        elif days <= 60:
            aging[cid]["over_60"] += bal
        else:
            aging[cid]["over_90"] += bal
        aging[cid]["total"] += bal

    items = list(aging.values())
    totals = {
        "customer_name": "TOTAL", "customer_id": 0,
        "current": sum(i["current"] for i in items),
        "over_30": sum(i["over_30"] for i in items),
        "over_60": sum(i["over_60"] for i in items),
        "over_90": sum(i["over_90"] for i in items),
        "total": sum(i["total"] for i in items),
    }
    # Convert Decimals to float for JSON
    for item in items:
        for k in ("current", "over_30", "over_60", "over_90", "total"):
            item[k] = float(item[k])
    for k in ("current", "over_30", "over_60", "over_90", "total"):
        totals[k] = float(totals[k])

    return {"as_of_date": as_of_date.isoformat(), "items": items, "totals": totals}


@router.get("/gst-return")
def gst_return_report(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    box9_adjustments: Decimal = Query(default=Decimal("0.00")),
    box13_adjustments: Decimal = Query(default=Decimal("0.00")),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    """GST101A return report."""
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()
    report, confirmed_return = _load_gst_return_report(
        db,
        start_date,
        end_date,
        box9_adjustments,
        box13_adjustments,
    )
    report["settlement"] = build_settlement_state(
        db,
        start_date,
        end_date,
        report,
        return_confirmed=confirmed_return is not None,
    )
    return report


@router.get("/gst-return/overview")
def gst_returns_overview(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    as_of_date = as_of_date or date.today()
    settings = get_settings(db)
    gst_period = settings.get("gst_period")
    fy_start = gst_financial_year_start(as_of_date)

    confirmed_returns = (
        db.query(GstReturn)
        .filter(GstReturn.status == GstReturnStatus.CONFIRMED)
        .order_by(GstReturn.end_date.desc(), GstReturn.id.desc())
        .all()
    )
    confirmed_return_periods = {(row.start_date, row.end_date) for row in confirmed_returns}

    legacy_settlements = (
        db.query(GstSettlement)
        .filter(GstSettlement.status == GstSettlementStatus.CONFIRMED)
        .order_by(GstSettlement.end_date.desc(), GstSettlement.id.desc())
        .all()
    )
    legacy_periods = {
        (row.start_date, row.end_date)
        for row in legacy_settlements
        if (row.start_date, row.end_date) not in confirmed_return_periods
    }

    open_periods = []
    for start_date_value, end_date_value in gst_period_windows(gst_period, fy_start, as_of_date):
        if (start_date_value, end_date_value) in confirmed_return_periods or (start_date_value, end_date_value) in legacy_periods:
            continue
        open_periods.append({
            "start_date": start_date_value.isoformat(),
            "end_date": end_date_value.isoformat(),
            "period_label": _period_label(start_date_value, end_date_value),
            "due_date": gst_due_date(end_date_value).isoformat(),
            "status": "current_period" if start_date_value <= as_of_date <= end_date_value else "due",
            "status_label": "Current period" if start_date_value <= as_of_date <= end_date_value else "Due",
            "net_gst": None,
            "box9_adjustments": "0.00",
            "box13_adjustments": "0.00",
        })

    historical_groups = []
    groups_by_year = {}

    def add_group_return(period: dict, end_date_value: date):
        financial_year = gst_financial_year_label(end_date_value)
        if financial_year not in groups_by_year:
            groups_by_year[financial_year] = {
                "financial_year": financial_year,
                "label": f"{financial_year} financial year",
                "returns": [],
            }
            historical_groups.append(groups_by_year[financial_year])
        groups_by_year[financial_year]["returns"].append(period)

    for confirmed_return in confirmed_returns:
        add_group_return(_historical_return_from_confirmed(confirmed_return), confirmed_return.end_date)

    for settlement in legacy_settlements:
        if (settlement.start_date, settlement.end_date) in confirmed_return_periods:
            continue
        add_group_return(_historical_return_from_legacy_settlement(settlement), settlement.end_date)

    return {
        "open_periods": open_periods,
        "historical_groups": historical_groups,
    }


@router.get("/gst-return/transactions")
def gst_return_transactions(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    box9_adjustments: Decimal = Query(default=Decimal("0.00")),
    box13_adjustments: Decimal = Query(default=Decimal("0.00")),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=250),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()
    report, _confirmed_return = _load_gst_transaction_report(
        db,
        start_date,
        end_date,
        box9_adjustments,
        box13_adjustments,
    )
    total_count = len(report["items"])
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "items": report["items"][start_index:end_index],
    }


class GstReturnConfirmRequest(BaseModel):
    start_date: date
    end_date: date
    box9_adjustments: Decimal = Decimal("0.00")
    box13_adjustments: Decimal = Decimal("0.00")


@router.post("/gst-return/confirm")
def confirm_gst_return(
    data: GstReturnConfirmRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = calculate_gst_return(
        db,
        data.start_date,
        data.end_date,
        box9_adjustments=_decimal_query_value(data.box9_adjustments),
        box13_adjustments=_decimal_query_value(data.box13_adjustments),
        include_items=False,
    )
    gst_return = confirm_gst_return_record(
        db,
        start_date=data.start_date,
        end_date=data.end_date,
        report=report,
    )
    return {
        "status": "confirmed",
        "gst_return_id": gst_return.id,
        "confirmed_at": gst_return.confirmed_at.isoformat() if gst_return.confirmed_at else None,
        "due_date": gst_return.due_date.isoformat(),
        "box9_adjustments": _decimal_text(gst_return.box9_adjustments),
        "box13_adjustments": _decimal_text(gst_return.box13_adjustments),
    }


class GstSettlementConfirmRequest(BaseModel):
    start_date: date
    end_date: date
    bank_transaction_id: int
    box9_adjustments: Decimal = Decimal("0.00")
    box13_adjustments: Decimal = Decimal("0.00")


@router.post("/gst-return/settlement")
def confirm_gst_settlement(
    data: GstSettlementConfirmRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    confirmed_return = get_confirmed_return(db, data.start_date, data.end_date)
    if not confirmed_return:
        raise HTTPException(status_code=400, detail="Confirm the GST return before confirming settlement")
    report = build_confirmed_return_report(confirmed_return)
    return confirm_settlement(
        db,
        start_date=data.start_date,
        end_date=data.end_date,
        bank_transaction_id=data.bank_transaction_id,
        report=report,
    )


@router.get("/sales-tax")
def sales_tax_report(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    """Compatibility alias for the NZ GST return report."""
    return gst_return_report(
        start_date=start_date,
        end_date=end_date,
        box9_adjustments=Decimal("0.00"),
        box13_adjustments=Decimal("0.00"),
        db=db,
        auth=auth,
    )


@router.get("/gst-return/pdf")
def gst_return_pdf(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    box9_adjustments: Decimal = Query(default=Decimal("0.00")),
    box13_adjustments: Decimal = Query(default=Decimal("0.00")),
    return_due_date: date = Query(default=None),
    phone: str = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()
    report, confirmed_return = _load_gst_return_report(
        db,
        start_date,
        end_date,
        box9_adjustments,
        box13_adjustments,
    )
    pdf_bytes = generate_gst101a_pdf(
        report,
        get_settings(db),
        return_due_date=_optional_query_value(return_due_date) or (confirmed_return.due_date if confirmed_return else None),
        phone=_optional_query_value(phone),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="GST101A_{start_date}_{end_date}.pdf"'},
    )


@router.get("/general-ledger")
def general_ledger(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    account_id: int = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    """CReportEngine::RunGLDetail() @ 0x00211400"""
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()

    q = (
        db.query(TransactionLine, Transaction, Account)
        .join(Transaction, TransactionLine.transaction_id == Transaction.id)
        .join(Account, TransactionLine.account_id == Account.id)
        .filter(Transaction.date >= start_date, Transaction.date <= end_date)
    )
    if account_id:
        q = q.filter(TransactionLine.account_id == account_id)

    q = q.order_by(Account.account_number, Transaction.date)
    results = q.all()

    entries_by_account = {}
    for tl, txn, acct in results:
        key = acct.id
        if key not in entries_by_account:
            entries_by_account[key] = {
                "account_id": acct.id,
                "account_number": acct.account_number,
                "account_name": acct.name,
                "account_type": acct.account_type.value,
                "entries": [],
                "total_debit": Decimal(0),
                "total_credit": Decimal(0),
            }
        entries_by_account[key]["entries"].append({
            "date": txn.date.isoformat(),
            "description": txn.description or tl.description or "",
            "reference": txn.reference or "",
            "debit": float(tl.debit),
            "credit": float(tl.credit),
        })
        entries_by_account[key]["total_debit"] += tl.debit
        entries_by_account[key]["total_credit"] += tl.credit

    accounts_list = list(entries_by_account.values())
    for a in accounts_list:
        a["total_debit"] = float(a["total_debit"])
        a["total_credit"] = float(a["total_credit"])

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "accounts": accounts_list,
    }


@router.get("/income-by-customer")
def income_by_customer(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    """CReportEngine::RunIncomeByCustomer() @ 0x00212000"""
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()

    invoices = (
        db.query(Invoice)
        .filter(Invoice.date >= start_date, Invoice.date <= end_date)
        .filter(Invoice.status != InvoiceStatus.VOID)
        .all()
    )

    by_customer = {}
    for inv in invoices:
        cid = inv.customer_id
        if cid not in by_customer:
            cname = inv.customer.name if inv.customer else "Unknown"
            by_customer[cid] = {
                "customer_id": cid,
                "customer_name": cname,
                "invoice_count": 0,
                "total_sales": Decimal(0),
                "total_paid": Decimal(0),
                "total_balance": Decimal(0),
            }
        by_customer[cid]["invoice_count"] += 1
        by_customer[cid]["total_sales"] += inv.total
        by_customer[cid]["total_paid"] += inv.amount_paid
        by_customer[cid]["total_balance"] += inv.balance_due

    items = sorted(by_customer.values(), key=lambda x: float(x["total_sales"]), reverse=True)
    for item in items:
        item["total_sales"] = float(item["total_sales"])
        item["total_paid"] = float(item["total_paid"])
        item["total_balance"] = float(item["total_balance"])

    grand_sales = sum(i["total_sales"] for i in items)
    grand_paid = sum(i["total_paid"] for i in items)
    grand_balance = sum(i["total_balance"] for i in items)

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "items": items,
        "total_sales": grand_sales,
        "total_paid": grand_paid,
        "total_balance": grand_balance,
    }


@router.get("/ap-aging")
def ap_aging(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    """AP Aging report — mirrors AR aging but for bills."""
    if not as_of_date:
        as_of_date = date.today()

    try:
        from app.models.bills import Bill, BillStatus
        from app.models.contacts import Vendor

        bills = (
            db.query(Bill)
            .filter(Bill.status.in_([BillStatus.UNPAID, BillStatus.PARTIAL]))
            .filter(Bill.balance_due > 0)
            .all()
        )

        aging = {}
        for bill in bills:
            vid = bill.vendor_id
            if vid not in aging:
                vname = db.query(Vendor.name).filter(Vendor.id == vid).scalar() or "Unknown"
                aging[vid] = {
                    "vendor_name": vname, "vendor_id": vid,
                    "current": Decimal(0), "over_30": Decimal(0),
                    "over_60": Decimal(0), "over_90": Decimal(0), "total": Decimal(0),
                }

            days = (as_of_date - bill.due_date).days if bill.due_date else 0
            bal = bill.balance_due
            if days <= 0:
                aging[vid]["current"] += bal
            elif days <= 30:
                aging[vid]["over_30"] += bal
            elif days <= 60:
                aging[vid]["over_60"] += bal
            else:
                aging[vid]["over_90"] += bal
            aging[vid]["total"] += bal

        items = list(aging.values())
        totals = {
            "vendor_name": "TOTAL", "vendor_id": 0,
            "current": sum(i["current"] for i in items),
            "over_30": sum(i["over_30"] for i in items),
            "over_60": sum(i["over_60"] for i in items),
            "over_90": sum(i["over_90"] for i in items),
            "total": sum(i["total"] for i in items),
        }
        for item in items:
            for k in ("current", "over_30", "over_60", "over_90", "total"):
                item[k] = float(item[k])
        for k in ("current", "over_30", "over_60", "over_90", "total"):
            totals[k] = float(totals[k])

        return {"as_of_date": as_of_date.isoformat(), "items": items, "totals": totals}
    except ImportError:
        return {"as_of_date": as_of_date.isoformat(), "items": [], "totals": {
            "vendor_name": "TOTAL", "vendor_id": 0,
            "current": 0, "over_30": 0, "over_60": 0, "over_90": 0, "total": 0,
        }}


@router.get("/customer-statement/{customer_id}/pdf")
def customer_statement_pdf(
    customer_id: int,
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    """CStatementPrintLayout::RenderPage() @ 0x00224000"""
    if not as_of_date:
        as_of_date = date.today()

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoices = (
        db.query(Invoice)
        .filter(Invoice.customer_id == customer_id)
        .filter(Invoice.status != InvoiceStatus.VOID)
        .filter(Invoice.date <= as_of_date)
        .order_by(Invoice.date)
        .all()
    )

    payments = (
        db.query(Payment)
        .filter(Payment.customer_id == customer_id)
        .filter(Payment.date <= as_of_date)
        .order_by(Payment.date)
        .all()
    )

    company = get_settings(db)
    pdf_bytes = generate_statement_pdf(customer, invoices, payments, company, as_of_date)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=Statement_{customer.name}.pdf"},
    )


@router.post("/customer-statement/{customer_id}/email")
def email_customer_statement(
    customer_id: int,
    data: StatementEmailRequest,
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
    request: Request = None,
):
    enforce_rate_limit(
        request,
        scope="email:documents",
        limit=5,
        window_seconds=60,
        detail="Too many document email requests. Please wait and try again.",
    )
    as_of_date = data.as_of_date or date.today()

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoices = (
        db.query(Invoice)
        .filter(Invoice.customer_id == customer_id)
        .filter(Invoice.status != InvoiceStatus.VOID)
        .filter(Invoice.date <= as_of_date)
        .order_by(Invoice.date)
        .all()
    )

    payments = (
        db.query(Payment)
        .filter(Payment.customer_id == customer_id)
        .filter(Payment.date <= as_of_date)
        .order_by(Payment.date)
        .all()
    )

    company = get_settings(db)
    try:
        pdf_bytes = generate_statement_pdf(customer, invoices, payments, company, as_of_date)
        html_body = render_document_email(
            document_label="Statement",
            recipient_name=customer.name,
            company_settings=company,
            action_label="As of",
            action_value=as_of_date,
            message="Please find attached your customer statement.",
        )
        send_document_email(
            db,
            to_email=data.recipient,
            subject=data.subject or f"Statement as at {as_of_date.isoformat()}",
            html_body=html_body,
            attachment_bytes=pdf_bytes,
            attachment_name=f"Statement_{customer_id}_{as_of_date.isoformat()}.pdf",
            entity_type="statement",
            entity_id=customer.id,
        )
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")

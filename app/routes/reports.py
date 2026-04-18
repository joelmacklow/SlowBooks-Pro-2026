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
from app.models.banking import BankAccount, BankTransaction
from app.models.gst_return import GstReturn, GstReturnStatus
from app.models.gst_settlement import GstSettlement, GstSettlementStatus
from app.models.transactions import Transaction, TransactionLine
from app.models.invoices import Invoice, InvoiceStatus
from app.models.payments import Payment
from app.models.contacts import Customer
from app.schemas.email import StatementEmailRequest
from pydantic import BaseModel
from app.services.email_service import render_document_email, send_document_email
from app.services.pdf_service import generate_report_pdf, generate_statement_pdf
from app.services.formatting import format_currency, format_date
from app.routes.settings import _get_all as get_settings
from app.services.accounting import get_default_bank_account_id
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


def _pdf_cell(text, align: str = "left", colspan: int = 1) -> dict:
    return {
        "text": text,
        "align": align,
        "colspan": colspan,
    }


def _pdf_row(*cells, class_name: str = "") -> dict:
    return {
        "cells": list(cells),
        "class_name": class_name,
    }


def _report_pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def _company_settings(db: Session) -> dict:
    return get_settings(db)


def _report_tables_profit_loss(report: dict, company: dict) -> list[dict]:
    rows = [_pdf_row(_pdf_cell("Income", colspan=2), class_name="section-row")]
    rows.extend(
        _pdf_row(
            _pdf_cell(entry["account_name"]),
            _pdf_cell(format_currency(entry["amount"], company), align="right"),
        )
        for entry in report["income"]
    )
    rows.append(_pdf_row(_pdf_cell("Total Income"), _pdf_cell(format_currency(report["total_income"], company), align="right"), class_name="total-row"))
    rows.append(_pdf_row(_pdf_cell("Cost of Goods Sold", colspan=2), class_name="section-row"))
    rows.extend(
        _pdf_row(
            _pdf_cell(entry["account_name"]),
            _pdf_cell(format_currency(abs(entry["amount"]), company), align="right"),
        )
        for entry in report["cogs"]
    )
    rows.append(_pdf_row(_pdf_cell("Gross Profit"), _pdf_cell(format_currency(report["gross_profit"], company), align="right"), class_name="total-row"))
    rows.append(_pdf_row(_pdf_cell("Expenses", colspan=2), class_name="section-row"))
    rows.extend(
        _pdf_row(
            _pdf_cell(entry["account_name"]),
            _pdf_cell(format_currency(abs(entry["amount"]), company), align="right"),
        )
        for entry in report["expenses"]
    )
    rows.append(_pdf_row(_pdf_cell("Total Expenses"), _pdf_cell(format_currency(report["total_expenses"], company), align="right"), class_name="total-row"))
    rows.append(_pdf_row(_pdf_cell("Net Income"), _pdf_cell(format_currency(report["net_income"], company), align="right"), class_name="total-row"))
    return [{
        "columns": [{"label": "Account"}, {"label": "Amount", "align": "right", "width": "24%"}],
        "rows": rows,
    }]


def _report_tables_balance_sheet(report: dict, company: dict) -> list[dict]:
    rows = [_pdf_row(_pdf_cell("Assets", colspan=2), class_name="section-row")]
    rows.extend(
        _pdf_row(_pdf_cell(entry["account_name"]), _pdf_cell(format_currency(abs(entry["amount"]), company), align="right"))
        for entry in report["assets"]
    )
    rows.append(_pdf_row(_pdf_cell("Total Assets"), _pdf_cell(format_currency(report["total_assets"], company), align="right"), class_name="total-row"))
    rows.append(_pdf_row(_pdf_cell("Liabilities", colspan=2), class_name="section-row"))
    rows.extend(
        _pdf_row(_pdf_cell(entry["account_name"]), _pdf_cell(format_currency(abs(entry["amount"]), company), align="right"))
        for entry in report["liabilities"]
    )
    rows.append(_pdf_row(_pdf_cell("Total Liabilities"), _pdf_cell(format_currency(report["total_liabilities"], company), align="right"), class_name="total-row"))
    rows.append(_pdf_row(_pdf_cell("Equity", colspan=2), class_name="section-row"))
    rows.extend(
        _pdf_row(_pdf_cell(entry["account_name"]), _pdf_cell(format_currency(abs(entry["amount"]), company), align="right"))
        for entry in report["equity"]
    )
    rows.append(_pdf_row(_pdf_cell("Total Equity"), _pdf_cell(format_currency(report["total_equity"], company), align="right"), class_name="total-row"))
    return [{
        "columns": [{"label": "Account"}, {"label": "Amount", "align": "right", "width": "24%"}],
        "rows": rows,
    }]


def _report_tables_trial_balance(report: dict, company: dict) -> list[dict]:
    rows = [
        _pdf_row(
            _pdf_cell(entry["account_number"] or ""),
            _pdf_cell(entry["account_name"]),
            _pdf_cell(entry["account_type"].replace("_", " ").title()),
            _pdf_cell(format_currency(entry["debit_balance"], company) if entry["debit_balance"] else "", align="right"),
            _pdf_cell(format_currency(entry["credit_balance"], company) if entry["credit_balance"] else "", align="right"),
        )
        for entry in report["accounts"]
    ]
    rows.append(
        _pdf_row(
            _pdf_cell("Total", colspan=3),
            _pdf_cell(format_currency(report["total_debit"], company), align="right"),
            _pdf_cell(format_currency(report["total_credit"], company), align="right"),
            class_name="total-row",
        )
    )
    return [{
        "columns": [
            {"label": "Account Code", "width": "12%"},
            {"label": "Account", "width": "30%"},
            {"label": "Account Type", "width": "16%"},
            {"label": "Debit", "align": "right", "width": "12%"},
            {"label": "Credit", "align": "right", "width": "12%"},
        ],
        "rows": rows,
        "empty_message": "No balances for this date.",
    }]


def _cash_flow_category_for_account(account: Account | None) -> str:
    if not account:
        return "operating"

    name = (account.name or "").lower()
    number = (account.account_number or "").lower()
    operating_asset_markers = (
        "receivable", "debtor", "inventory", "stock", "prepayment", "undeposited", "gst", "tax"
    )
    financing_liability_markers = ("loan", "mortgage", "lease", "note payable", "note")

    if account.account_type in (AccountType.INCOME, AccountType.EXPENSE, AccountType.COGS):
        return "operating"
    if account.account_type == AccountType.EQUITY:
        return "financing"
    if account.account_type == AccountType.LIABILITY:
        if any(marker in name for marker in financing_liability_markers):
            return "financing"
        return "operating"
    if any(marker in name for marker in operating_asset_markers) or number.startswith("11"):
        return "operating"
    return "investing"


def _cash_account_ids(db: Session) -> set[int]:
    ids = {
        int(account_id)
        for account_id, in (
            db.query(BankAccount.account_id)
            .filter(BankAccount.is_active == True, BankAccount.account_id.is_not(None))
            .all()
        )
        if account_id is not None
    }
    default_bank_id = get_default_bank_account_id(db, allow_create=False)
    if default_bank_id:
        ids.add(int(default_bank_id))
    return ids


def _opening_cash_balance(db: Session, cash_account_ids: set[int], start_date: date) -> Decimal:
    rows = (
        db.query(TransactionLine.debit, TransactionLine.credit)
        .join(Transaction, TransactionLine.transaction_id == Transaction.id)
        .filter(TransactionLine.account_id.in_(cash_account_ids), Transaction.date < start_date)
        .all()
    )
    return sum((Decimal(str(debit or 0)) - Decimal(str(credit or 0)) for debit, credit in rows), Decimal("0.00"))


def _report_tables_cash_flow(report: dict, company: dict) -> list[dict]:
    tables = []
    label_map = {
        "operating": "Operating Activities",
        "investing": "Investing Activities",
        "financing": "Financing Activities",
    }
    for key in ("operating", "investing", "financing"):
        section = report[key]
        rows = [
            _pdf_row(
                _pdf_cell(format_date(entry["date"], company)),
                _pdf_cell(entry["description"]),
                _pdf_cell(entry["reference"]),
                _pdf_cell(format_currency(entry["amount"], company), align="right"),
            )
            for entry in section["items"]
        ]
        rows.append(
            _pdf_row(
                _pdf_cell(f'Net cash from {label_map[key].lower()}', colspan=3),
                _pdf_cell(format_currency(section["total"], company), align="right"),
                class_name="total-row",
            )
        )
        tables.append({
            "title": label_map[key],
            "columns": [
                {"label": "Date", "width": "16%"},
                {"label": "Description", "width": "46%"},
                {"label": "Reference", "width": "18%"},
                {"label": "Amount", "align": "right", "width": "20%"},
            ],
            "rows": rows,
            "empty_message": f'No {label_map[key].lower()} cash flows for this period.',
        })
    tables.append({
        "title": "Cash Summary",
        "columns": [
            {"label": "Measure", "width": "70%"},
            {"label": "Amount", "align": "right", "width": "30%"},
        ],
        "rows": [
            _pdf_row(_pdf_cell("Opening cash balance"), _pdf_cell(format_currency(report["opening_cash"], company), align="right")),
            _pdf_row(_pdf_cell("Net increase / (decrease) in cash"), _pdf_cell(format_currency(report["net_cash_change"], company), align="right")),
            _pdf_row(_pdf_cell("Closing cash balance"), _pdf_cell(format_currency(report["closing_cash"], company), align="right"), class_name="total-row"),
        ],
    })
    return tables


def _report_tables_aging(report: dict, company: dict, party_label: str) -> list[dict]:
    label_key = "customer_name" if party_label == "Customer" else "vendor_name"
    rows = [
        _pdf_row(
            _pdf_cell(entry[label_key]),
            _pdf_cell(format_currency(entry["current"], company), align="right"),
            _pdf_cell(format_currency(entry["over_30"], company), align="right"),
            _pdf_cell(format_currency(entry["over_60"], company), align="right"),
            _pdf_cell(format_currency(entry["over_90"], company), align="right"),
            _pdf_cell(format_currency(entry["total"], company), align="right"),
        )
        for entry in report["items"]
    ]
    totals = report["totals"]
    rows.append(
        _pdf_row(
            _pdf_cell("Total"),
            _pdf_cell(format_currency(totals["current"], company), align="right"),
            _pdf_cell(format_currency(totals["over_30"], company), align="right"),
            _pdf_cell(format_currency(totals["over_60"], company), align="right"),
            _pdf_cell(format_currency(totals["over_90"], company), align="right"),
            _pdf_cell(format_currency(totals["total"], company), align="right"),
            class_name="total-row",
        )
    )
    return [{
        "columns": [
            {"label": party_label, "width": "26%"},
            {"label": "Current", "align": "right"},
            {"label": "1-30", "align": "right"},
            {"label": "31-60", "align": "right"},
            {"label": "61-90+", "align": "right"},
            {"label": "Total", "align": "right"},
        ],
        "rows": rows,
        "empty_message": f"No outstanding {party_label.lower()} balances.",
    }]


def _report_tables_income_by_customer(report: dict, company: dict) -> list[dict]:
    invoice_total = sum(item["invoice_count"] for item in report["items"])
    rows = [
        _pdf_row(
            _pdf_cell(entry["customer_name"]),
            _pdf_cell(str(entry["invoice_count"]), align="right"),
            _pdf_cell(format_currency(entry["total_sales"], company), align="right"),
            _pdf_cell(format_currency(entry["total_paid"], company), align="right"),
            _pdf_cell(format_currency(entry["total_balance"], company), align="right"),
        )
        for entry in report["items"]
    ]
    rows.append(
        _pdf_row(
            _pdf_cell("Total"),
            _pdf_cell(str(invoice_total), align="right"),
            _pdf_cell(format_currency(report["total_sales"], company), align="right"),
            _pdf_cell(format_currency(report["total_paid"], company), align="right"),
            _pdf_cell(format_currency(report["total_balance"], company), align="right"),
            class_name="total-row",
        )
    )
    return [{
        "columns": [
            {"label": "Customer", "width": "32%"},
            {"label": "Invoices", "align": "right", "width": "12%"},
            {"label": "Sales", "align": "right", "width": "18%"},
            {"label": "Paid", "align": "right", "width": "18%"},
            {"label": "Balance", "align": "right", "width": "20%"},
        ],
        "rows": rows,
        "empty_message": "No sales data for this period.",
    }]


def _report_tables_general_ledger(report: dict, company: dict) -> list[dict]:
    tables = []
    for account in report["accounts"]:
        rows = [
            _pdf_row(
                _pdf_cell(format_date(entry["date"], company)),
                _pdf_cell(entry["description"]),
                _pdf_cell(entry["reference"]),
                _pdf_cell(format_currency(entry["debit"], company) if entry["debit"] else "", align="right"),
                _pdf_cell(format_currency(entry["credit"], company) if entry["credit"] else "", align="right"),
            )
            for entry in account["entries"]
        ]
        rows.append(
            _pdf_row(
                _pdf_cell("Total", colspan=3),
                _pdf_cell(format_currency(account["total_debit"], company), align="right"),
                _pdf_cell(format_currency(account["total_credit"], company), align="right"),
                class_name="total-row",
            )
        )
        tables.append({
            "title": f'{account["account_number"] or ""} - {account["account_name"]}'.strip(" -"),
            "columns": [
                {"label": "Date", "width": "16%"},
                {"label": "Description", "width": "36%"},
                {"label": "Reference", "width": "18%"},
                {"label": "Debit", "align": "right", "width": "15%"},
                {"label": "Credit", "align": "right", "width": "15%"},
            ],
            "rows": rows,
            "empty_message": "No journal entries found.",
        })
    return tables or [{
        "columns": [{"label": "General Ledger"}],
        "rows": [],
        "empty_message": "No journal entries found for this period.",
    }]


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


@router.get("/profit-loss/pdf")
def profit_loss_pdf(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = profit_loss(start_date=start_date, end_date=end_date, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="Profit & Loss",
        company_settings=company,
        subtitle=f'{format_date(report["start_date"], company)} - {format_date(report["end_date"], company)}',
        tables=_report_tables_profit_loss(report, company),
    )
    return _report_pdf_response(pdf_bytes, f'ProfitLoss_{report["start_date"]}_{report["end_date"]}.pdf')


@router.get("/balance-sheet/pdf")
def balance_sheet_pdf(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = balance_sheet(as_of_date=as_of_date, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="Balance Sheet",
        company_settings=company,
        subtitle=f'As of {format_date(report["as_of_date"], company)}',
        tables=_report_tables_balance_sheet(report, company),
    )
    return _report_pdf_response(pdf_bytes, f'BalanceSheet_{report["as_of_date"]}.pdf')


@router.get("/trial-balance")
def trial_balance(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    if not as_of_date:
        as_of_date = date.today()

    results = (
        db.query(
            Account.id,
            Account.account_number,
            Account.name,
            Account.account_type,
            sqlfunc.coalesce(sqlfunc.sum(TransactionLine.debit), 0),
            sqlfunc.coalesce(sqlfunc.sum(TransactionLine.credit), 0),
        )
        .join(TransactionLine, TransactionLine.account_id == Account.id)
        .join(Transaction, TransactionLine.transaction_id == Transaction.id)
        .filter(Transaction.date <= as_of_date)
        .group_by(Account.id, Account.account_number, Account.name, Account.account_type)
        .all()
    )

    accounts = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for account_id, account_number, account_name, account_type, debit_total, credit_total in results:
        net_balance = Decimal(str(debit_total or 0)) - Decimal(str(credit_total or 0))
        if net_balance == 0:
            continue

        debit_balance = net_balance if net_balance > 0 else Decimal("0.00")
        credit_balance = -net_balance if net_balance < 0 else Decimal("0.00")
        total_debit += debit_balance
        total_credit += credit_balance
        accounts.append({
            "account_id": account_id,
            "account_number": account_number,
            "account_name": account_name,
            "account_type": account_type.value,
            "debit_balance": float(debit_balance),
            "credit_balance": float(credit_balance),
        })

    accounts.sort(key=lambda row: (row["account_number"] is None, row["account_number"] or "", row["account_name"]))

    return {
        "as_of_date": as_of_date.isoformat(),
        "accounts": accounts,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
    }


@router.get("/trial-balance/pdf")
def trial_balance_pdf(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = trial_balance(as_of_date=as_of_date, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="Trial Balance",
        company_settings=company,
        subtitle=f'As of {format_date(report["as_of_date"], company)}',
        tables=_report_tables_trial_balance(report, company),
    )
    return _report_pdf_response(pdf_bytes, f'TrialBalance_{report["as_of_date"]}.pdf')


@router.get("/cash-flow")
def cash_flow_report(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()

    cash_account_ids = _cash_account_ids(db)
    if not cash_account_ids:
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "cash_account_ids": [],
            "operating": {"items": [], "total": 0.0},
            "investing": {"items": [], "total": 0.0},
            "financing": {"items": [], "total": 0.0},
            "opening_cash": 0.0,
            "closing_cash": 0.0,
            "net_cash_change": 0.0,
        }

    txns = (
        db.query(Transaction)
        .filter(Transaction.date >= start_date, Transaction.date <= end_date)
        .order_by(Transaction.date, Transaction.id)
        .all()
    )

    sections = {
        "operating": {"items": [], "total": Decimal("0.00")},
        "investing": {"items": [], "total": Decimal("0.00")},
        "financing": {"items": [], "total": Decimal("0.00")},
    }

    for txn in txns:
        cash_lines = [line for line in txn.lines if line.account_id in cash_account_ids]
        counterpart_lines = [line for line in txn.lines if line.account_id not in cash_account_ids]
        if not cash_lines or not counterpart_lines:
            continue

        net_cash = sum((Decimal(str(line.debit or 0)) - Decimal(str(line.credit or 0)) for line in cash_lines), Decimal("0.00"))
        if net_cash == 0:
            continue

        categories = {_cash_flow_category_for_account(line.account) for line in counterpart_lines}
        if categories == {"financing"}:
            section_key = "financing"
        elif categories == {"investing"}:
            section_key = "investing"
        elif "operating" in categories:
            section_key = "operating"
        elif "financing" in categories and "investing" not in categories:
            section_key = "financing"
        else:
            section_key = "investing"

        sections[section_key]["items"].append({
            "transaction_id": txn.id,
            "date": txn.date.isoformat(),
            "description": txn.description or txn.source_type or "Cash movement",
            "reference": txn.reference or "",
            "amount": float(net_cash),
            "source_type": txn.source_type or "",
        })
        sections[section_key]["total"] += net_cash

    opening_cash = _opening_cash_balance(db, cash_account_ids, start_date)
    net_cash_change = sum((section["total"] for section in sections.values()), Decimal("0.00"))
    closing_cash = opening_cash + net_cash_change

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "cash_account_ids": sorted(cash_account_ids),
        "operating": {"items": sections["operating"]["items"], "total": float(sections["operating"]["total"])},
        "investing": {"items": sections["investing"]["items"], "total": float(sections["investing"]["total"])},
        "financing": {"items": sections["financing"]["items"], "total": float(sections["financing"]["total"])},
        "opening_cash": float(opening_cash),
        "closing_cash": float(closing_cash),
        "net_cash_change": float(net_cash_change),
    }


@router.get("/cash-flow/pdf")
def cash_flow_pdf(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = cash_flow_report(start_date=start_date, end_date=end_date, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="Cash Flow",
        company_settings=company,
        subtitle=f'{format_date(report["start_date"], company)} - {format_date(report["end_date"], company)}',
        tables=_report_tables_cash_flow(report, company),
    )
    return _report_pdf_response(pdf_bytes, f'CashFlow_{report["start_date"]}_{report["end_date"]}.pdf')


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


@router.get("/ar-aging/pdf")
def ar_aging_pdf(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = ar_aging(as_of_date=as_of_date, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="Accounts Receivable Aging",
        company_settings=company,
        subtitle=f'As of {format_date(report["as_of_date"], company)}',
        tables=_report_tables_aging(report, company, "Customer"),
        landscape=True,
    )
    return _report_pdf_response(pdf_bytes, f'ARAging_{report["as_of_date"]}.pdf')


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
        headers={"Content-Disposition": f'inline; filename="GST101A_{start_date}_{end_date}.pdf"'},
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


@router.get("/general-ledger/pdf")
def general_ledger_pdf(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    account_id: int = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = general_ledger(start_date=start_date, end_date=end_date, account_id=account_id, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="General Ledger",
        company_settings=company,
        subtitle=f'{format_date(report["start_date"], company)} - {format_date(report["end_date"], company)}',
        tables=_report_tables_general_ledger(report, company),
        landscape=True,
    )
    return _report_pdf_response(pdf_bytes, f'GeneralLedger_{report["start_date"]}_{report["end_date"]}.pdf')


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


@router.get("/income-by-customer/pdf")
def income_by_customer_pdf(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = income_by_customer(start_date=start_date, end_date=end_date, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="Income by Customer",
        company_settings=company,
        subtitle=f'{format_date(report["start_date"], company)} - {format_date(report["end_date"], company)}',
        tables=_report_tables_income_by_customer(report, company),
        landscape=True,
    )
    return _report_pdf_response(pdf_bytes, f'IncomeByCustomer_{report["start_date"]}_{report["end_date"]}.pdf')


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


@router.get("/ap-aging/pdf")
def ap_aging_pdf(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db),
    auth=Depends(require_permissions("accounts.manage")),
):
    report = ap_aging(as_of_date=as_of_date, db=db, auth=auth)
    company = _company_settings(db)
    pdf_bytes = generate_report_pdf(
        title="Accounts Payable Aging",
        company_settings=company,
        subtitle=f'As of {format_date(report["as_of_date"], company)}',
        tables=_report_tables_aging(report, company, "Vendor"),
        landscape=True,
    )
    return _report_pdf_response(pdf_bytes, f'APAging_{report["as_of_date"]}.pdf')


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

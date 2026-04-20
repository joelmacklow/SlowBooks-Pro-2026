from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contacts import Customer
from app.models.invoices import Invoice, InvoiceStatus
from app.models.payments import Payment
from app.services.auth import require_permissions
from app.services.dashboard_metrics import (
    build_dashboard_account_watchlist,
    build_dashboard_bank_account_summaries,
    build_dashboard_cash_flow,
    build_dashboard_invoice_summary,
    build_dashboard_monthly_revenue,
    build_dashboard_profit_summary,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
FINANCIALS_PERMISSION = "dashboard.financials.view"


def _can_view_financial_dashboard(auth) -> bool:
    return FINANCIALS_PERMISSION in getattr(auth, "permissions", frozenset())


@router.get("")
def get_dashboard(db: Session = Depends(get_db), auth=Depends(require_permissions())):
    today = date.today()
    customer_count = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar()
    if not _can_view_financial_dashboard(auth):
        return {
            "customer_count": customer_count,
            "financial_overview_available": False,
        }

    invoice_summary = build_dashboard_invoice_summary(db, today=today)
    recent_invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(5).all()
    recent_payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(5).all()
    bank_accounts = build_dashboard_bank_account_summaries(db)
    watchlist = build_dashboard_account_watchlist(db, today=today)

    total_payables = 0.0
    overdue_bills = 0
    try:
        from app.models.bills import Bill, BillStatus

        total_payables = float(db.query(func.coalesce(func.sum(Bill.balance_due), 0)).filter(Bill.status.in_([BillStatus.UNPAID, BillStatus.PARTIAL])).scalar())
        overdue_bills = db.query(func.count(Bill.id)).filter(Bill.status.in_([BillStatus.UNPAID, BillStatus.PARTIAL]), Bill.due_date < func.current_date()).scalar()
    except Exception:
        pass

    return {
        "financial_overview_available": True,
        "total_receivables": invoice_summary["total_receivables"],
        "overdue_count": invoice_summary["overdue_count"],
        "customer_count": customer_count,
        "total_payables": total_payables,
        "overdue_bills": overdue_bills,
        "invoice_summary": invoice_summary,
        "bank_accounts": bank_accounts,
        "watchlist": watchlist,
        "recent_invoices": [{"id": inv.id, "invoice_number": inv.invoice_number, "customer_id": inv.customer_id, "total": float(inv.total), "balance_due": float(inv.balance_due), "status": inv.status.value, "date": inv.date.isoformat()} for inv in recent_invoices],
        "recent_payments": [{"id": p.id, "customer_id": p.customer_id, "amount": float(p.amount), "date": p.date.isoformat(), "method": p.method} for p in recent_payments],
        "bank_balances": [{"id": ba["id"], "name": ba["name"], "balance": ba["balance"]} for ba in bank_accounts],
    }


@router.get("/charts")
def get_dashboard_charts(db: Session = Depends(get_db), auth=Depends(require_permissions(FINANCIALS_PERMISSION))):
    today = date.today()
    invoices = db.query(Invoice).filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL]), Invoice.balance_due > 0).all()

    aging_current = Decimal(0)
    aging_30 = Decimal(0)
    aging_60 = Decimal(0)
    aging_90 = Decimal(0)

    for inv in invoices:
        days = (today - inv.due_date).days if inv.due_date else 0
        if days <= 0:
            aging_current += inv.balance_due
        elif days <= 30:
            aging_30 += inv.balance_due
        elif days <= 60:
            aging_60 += inv.balance_due
        else:
            aging_90 += inv.balance_due

    return {
        "aging_current": float(aging_current),
        "aging_30": float(aging_30),
        "aging_60": float(aging_60),
        "aging_90": float(aging_90),
        "monthly_revenue": build_dashboard_monthly_revenue(db, today=today),
        "profit_summary": build_dashboard_profit_summary(db, today=today),
        "cash_flow": build_dashboard_cash_flow(db, today=today, months=6),
    }

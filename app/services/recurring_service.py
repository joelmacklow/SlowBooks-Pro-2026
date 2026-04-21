# ============================================================================
# Recurring Invoice Service — generates invoices from recurring templates
# Feature 2: Infrastructure C (background scheduler / cron)
# ============================================================================

from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from sqlalchemy.orm import Session

from app.models.recurring import RecurringInvoice
from app.models.invoices import Invoice, InvoiceLine
from app.models.items import Item
from app.routes.settings import _get_all as get_settings
from app.services.accounting import (
    create_journal_entry, get_ar_account_id,
    get_default_income_account_id, get_gst_account_id,
)
from app.services.document_sequences import allocate_document_number
from app.services.gst_calculations import calculate_document_gst, prices_include_gst
from app.services.gst_lines import stored_gst_line_inputs
from app.services.payment_terms import resolve_due_date_for_terms


def _next_invoice_number(db: Session) -> str:
    return allocate_document_number(
        db,
        model=Invoice,
        field_name="invoice_number",
        prefix_key="invoice_prefix",
        next_key="invoice_next_number",
        default_prefix="",
        default_next_number="1001",
    )


def _advance_next_due(current: date, frequency: str) -> date:
    if frequency == "weekly":
        return current + timedelta(weeks=1)
    elif frequency == "monthly":
        return current + relativedelta(months=1)
    elif frequency == "quarterly":
        return current + relativedelta(months=3)
    elif frequency == "yearly":
        return current + relativedelta(years=1)
    return current + relativedelta(months=1)


def calculate_next_due(start_date: date, frequency: str, *, as_of: date = None) -> date:
    target = as_of or date.today()
    next_due = start_date
    while next_due < target:
        next_due = _advance_next_due(next_due, frequency)
    return next_due


def generate_due_invoices(db: Session, as_of: date = None) -> list[int]:
    """Generate all invoices that are due on or before as_of date.
    Returns list of created invoice IDs."""
    if as_of is None:
        as_of = date.today()

    recurrings = db.query(RecurringInvoice).filter(
        RecurringInvoice.is_active == True,
        RecurringInvoice.next_due <= as_of,
    ).all()

    created_ids = []
    ar_id = get_ar_account_id(db)
    default_income_id = get_default_income_account_id(db)
    tax_account_id = get_gst_account_id(db)

    for rec in recurrings:
        # Check end date
        if rec.end_date and rec.next_due > rec.end_date:
            rec.is_active = False
            continue

        invoice_number = _next_invoice_number(db)

        gst_inputs = stored_gst_line_inputs(db, rec.lines)
        gst_totals = calculate_document_gst(
            gst_inputs,
            prices_include_gst=prices_include_gst(db),
            gst_context="sales",
        )

        due_date = resolve_due_date_for_terms(rec.next_due, rec.terms, get_settings(db).get("payment_terms_config"))

        invoice = Invoice(
            invoice_number=invoice_number, customer_id=rec.customer_id,
            date=rec.next_due, due_date=due_date, terms=rec.terms,
            subtotal=gst_totals.subtotal, tax_rate=gst_totals.effective_tax_rate, tax_amount=gst_totals.tax_amount,
            total=gst_totals.total, balance_due=gst_totals.total, notes=rec.notes,
        )
        db.add(invoice)
        db.flush()

        for i, rline in enumerate(rec.lines):
            db.add(InvoiceLine(
                invoice_id=invoice.id, item_id=rline.item_id,
                description=rline.description, quantity=rline.quantity,
                rate=rline.rate, amount=gst_totals.lines[i].net_amount,
                gst_code=rline.gst_code, gst_rate=rline.gst_rate,
                line_order=rline.line_order,
            ))

        # Journal entry
        if ar_id and default_income_id:
            journal_lines = [{
                "account_id": ar_id, "debit": gst_totals.total, "credit": Decimal("0"),
                "description": f"Recurring Invoice #{invoice_number}",
            }]
            for i, rline in enumerate(rec.lines):
                line_amt = gst_totals.lines[i].net_amount
                if line_amt == 0:
                    continue
                income_id = default_income_id
                if rline.item_id:
                    item = db.query(Item).filter(Item.id == rline.item_id).first()
                    if item and item.income_account_id:
                        income_id = item.income_account_id
                journal_lines.append({
                    "account_id": income_id, "debit": Decimal("0"), "credit": line_amt,
                    "description": rline.description or "",
                })
            if gst_totals.tax_amount > 0 and tax_account_id:
                journal_lines.append({
                    "account_id": tax_account_id, "debit": Decimal("0"), "credit": gst_totals.tax_amount,
                    "description": "GST",
                })
            txn = create_journal_entry(
                db, rec.next_due, f"Recurring Invoice #{invoice_number}",
                journal_lines, source_type="invoice", source_id=invoice.id,
                reference=invoice_number,
            )
            invoice.transaction_id = txn.id

        # Advance next due date
        rec.next_due = _advance_next_due(rec.next_due, rec.frequency)
        rec.invoices_created += 1
        if rec.end_date and rec.next_due > rec.end_date:
            rec.is_active = False

        created_ids.append(invoice.id)

    db.commit()
    return created_ids

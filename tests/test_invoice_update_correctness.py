import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base
from app.models.accounts import Account, AccountType
from app.models.contacts import Customer
from app.models.invoices import Invoice
from app.models.transactions import TransactionLine


class InvoiceUpdateCorrectnessTests(unittest.TestCase):
    def setUp(self):
        from app.models.gst import GstCode  # noqa: F401
        from app.models.payments import Payment, PaymentAllocation  # noqa: F401
        from app.services import closing_date as closing_date_service

        company_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        master_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=company_engine)
        Base.metadata.create_all(bind=master_engine)
        self.Session = sessionmaker(bind=company_engine)
        self.MasterSession = sessionmaker(bind=master_engine)
        self.closing_date_service = closing_date_service
        self._original_open_master_session = getattr(closing_date_service, "_open_master_session", None)
        self._original_database_name_for_session = getattr(closing_date_service, "_database_name_for_session", None)
        closing_date_service._open_master_session = self.MasterSession
        closing_date_service._database_name_for_session = lambda _db: "bookkeeper"

    def tearDown(self):
        if self._original_open_master_session is not None:
            self.closing_date_service._open_master_session = self._original_open_master_session
        if self._original_database_name_for_session is not None:
            self.closing_date_service._database_name_for_session = self._original_database_name_for_session

    def _seed_customer_and_accounts(self, db):
        customer = Customer(name="Aroha Ltd")
        db.add_all([
            customer,
            Account(name="Accounts Receivable", account_number="1100", account_type=AccountType.ASSET),
            Account(name="GST", account_number="2200", account_type=AccountType.LIABILITY),
            Account(name="Service Income", account_number="4000", account_type=AccountType.INCOME),
            Account(name="Receipt Clearing", account_number="1200", account_type=AccountType.ASSET),
        ])
        db.commit()
        return customer

    def _journal_totals(self, db, transaction_id):
        lines = db.query(TransactionLine).filter(TransactionLine.transaction_id == transaction_id).all()
        return (
            sum((Decimal(str(line.debit)) for line in lines), Decimal("0.00")),
            sum((Decimal(str(line.credit)) for line in lines), Decimal("0.00")),
        )

    def test_tax_rate_only_update_recomputes_from_existing_gst_lines(self):
        from app.routes.invoices import create_invoice, update_invoice
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate, InvoiceUpdate

        with self.Session() as db:
            customer = self._seed_customer_and_accounts(db)
            created = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 20),
                lines=[InvoiceLineCreate(description="Consulting", quantity=1, rate=Decimal("100.00"), gst_code="GST15")],
            ), db=db)

            updated = update_invoice(created.id, InvoiceUpdate(tax_rate=Decimal("0.9900")), db=db)
            stored = db.query(Invoice).filter(Invoice.id == created.id).one()
            dr, cr = self._journal_totals(db, stored.transaction_id)

        self.assertEqual(updated.subtotal, Decimal("100.00"))
        self.assertEqual(updated.tax_amount, Decimal("15.00"))
        self.assertEqual(updated.total, Decimal("115.00"))
        self.assertEqual(updated.tax_rate, Decimal("0.1500"))
        self.assertEqual(stored.tax_rate, Decimal("0.1500"))
        self.assertEqual(dr, Decimal("115.00"))
        self.assertEqual(cr, Decimal("115.00"))

    def test_editing_partially_paid_invoice_downward_clamps_balance_due_at_zero(self):
        from app.routes.invoices import create_invoice, update_invoice
        from app.routes.payments import create_payment
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate, InvoiceUpdate
        from app.schemas.payments import PaymentAllocationCreate, PaymentCreate

        with self.Session() as db:
            customer = self._seed_customer_and_accounts(db)
            created = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 20),
                lines=[InvoiceLineCreate(description="Consulting", quantity=1, rate=Decimal("100.00"), gst_code="GST15")],
            ), db=db)
            create_payment(PaymentCreate(
                customer_id=customer.id,
                date=date(2026, 4, 21),
                amount=Decimal("50.00"),
                allocations=[PaymentAllocationCreate(invoice_id=created.id, amount=Decimal("50.00"))],
            ), db=db)

            updated = update_invoice(created.id, InvoiceUpdate(
                lines=[InvoiceLineCreate(description="Reduced", quantity=1, rate=Decimal("40.00"), gst_code="GST15")],
            ), db=db)
            stored = db.query(Invoice).filter(Invoice.id == created.id).one()

        self.assertEqual(updated.total, Decimal("46.00"))
        self.assertEqual(updated.amount_paid, Decimal("50.00"))
        self.assertEqual(updated.balance_due, Decimal("0.00"))
        self.assertEqual(stored.balance_due, Decimal("0.00"))

    def test_paid_invoice_cannot_be_updated_or_voided(self):
        from app.routes.invoices import create_invoice, update_invoice, void_invoice
        from app.routes.payments import create_payment
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate, InvoiceUpdate
        from app.schemas.payments import PaymentAllocationCreate, PaymentCreate

        with self.Session() as db:
            customer = self._seed_customer_and_accounts(db)
            created = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 20),
                lines=[InvoiceLineCreate(description="Consulting", quantity=1, rate=Decimal("100.00"), gst_code="GST15")],
            ), db=db)
            create_payment(PaymentCreate(
                customer_id=customer.id,
                date=date(2026, 4, 21),
                amount=Decimal("115.00"),
                allocations=[PaymentAllocationCreate(invoice_id=created.id, amount=Decimal("115.00"))],
            ), db=db)

            with self.assertRaises(HTTPException) as update_ctx:
                update_invoice(created.id, InvoiceUpdate(notes="Should fail"), db=db)

            with self.assertRaises(HTTPException) as void_ctx:
                void_invoice(created.id, db=db)

            stored = db.query(Invoice).filter(Invoice.id == created.id).one()

        self.assertEqual(update_ctx.exception.status_code, 400)
        self.assertIn("paid", update_ctx.exception.detail.lower())
        self.assertEqual(void_ctx.exception.status_code, 400)
        self.assertIn("paid", void_ctx.exception.detail.lower())
        self.assertEqual(stored.status.value if hasattr(stored.status, "value") else stored.status, "paid")


if __name__ == "__main__":
    unittest.main()

import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class CreditNoteApplicationAuditTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_credit_memo_detail_includes_applied_invoice_numbers_and_amounts(self):
        from app.models.contacts import Customer
        from app.models.credit_memos import CreditApplication, CreditMemo, CreditMemoStatus
        from app.models.invoices import Invoice, InvoiceStatus
        from app.routes.credit_memos import get_credit_memo

        with self.Session() as db:
            customer = Customer(name="Aroha Ltd")
            invoice = Invoice(
                invoice_number="INV-1011",
                customer=customer,
                date=date(2026, 4, 16),
                due_date=date(2026, 4, 30),
                status=InvoiceStatus.PARTIAL,
                subtotal=Decimal("100.00"),
                tax_rate=Decimal("0.1500"),
                tax_amount=Decimal("15.00"),
                total=Decimal("115.00"),
                amount_paid=Decimal("20.00"),
                balance_due=Decimal("95.00"),
            )
            memo = CreditMemo(
                memo_number="CM-1001",
                customer=customer,
                date=date(2026, 4, 16),
                status=CreditMemoStatus.APPLIED,
                subtotal=Decimal("50.00"),
                tax_rate=Decimal("0.1500"),
                tax_amount=Decimal("7.50"),
                total=Decimal("57.50"),
                amount_applied=Decimal("20.00"),
                balance_remaining=Decimal("37.50"),
            )
            db.add_all([customer, invoice, memo])
            db.flush()
            db.add(CreditApplication(credit_memo_id=memo.id, invoice_id=invoice.id, amount=Decimal("20.00")))
            db.commit()

            response = get_credit_memo(memo.id, db=db, auth=None)

        self.assertEqual(len(response.applications), 1)
        self.assertEqual(response.applications[0]["invoice_id"], invoice.id)
        self.assertEqual(response.applications[0]["invoice_number"], "INV-1011")
        self.assertEqual(Decimal(str(response.applications[0]["amount"])), Decimal("20.00"))


if __name__ == "__main__":
    unittest.main()

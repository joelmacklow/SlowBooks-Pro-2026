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


class InvoiceCreditApplicationAuditTests(unittest.TestCase):
    def setUp(self):
        from app.models import (  # noqa: F401
            Account, Customer, Vendor, Item, Invoice, InvoiceLine,
            Payment, PaymentAllocation, Estimate, EstimateLine, Transaction,
            TransactionLine, Settings, GstCode, BankAccount, Reconciliation,
            BankTransaction, Company, PayRun, PayStub, Employee,
            CreditMemo, CreditMemoLine, CreditApplication,
        )

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_invoice_detail_includes_applied_credit_note_numbers_and_amounts(self):
        from app.models.contacts import Customer
        from app.models.credit_memos import CreditApplication, CreditMemo, CreditMemoStatus
        from app.models.invoices import Invoice, InvoiceStatus
        from app.routes.invoices import get_invoice

        with self.Session() as db:
            customer = Customer(name="Aroha Ltd")
            db.add(customer)
            db.flush()

            invoice = Invoice(
                invoice_number="INV-1011",
                customer_id=customer.id,
                status=InvoiceStatus.PARTIAL,
                date=date(2026, 4, 18),
                subtotal=Decimal("100.00"),
                tax_rate=Decimal("0.1500"),
                tax_amount=Decimal("15.00"),
                total=Decimal("115.00"),
                amount_paid=Decimal("20.00"),
                balance_due=Decimal("95.00"),
            )
            db.add(invoice)
            db.flush()

            memo = CreditMemo(
                memo_number="CM-2011",
                customer_id=customer.id,
                status=CreditMemoStatus.APPLIED,
                date=date(2026, 4, 19),
                subtotal=Decimal("20.00"),
                tax_rate=Decimal("0.1500"),
                tax_amount=Decimal("0.00"),
                total=Decimal("20.00"),
                amount_applied=Decimal("20.00"),
                balance_remaining=Decimal("0.00"),
            )
            db.add(memo)
            db.flush()

            db.add(CreditApplication(credit_memo_id=memo.id, invoice_id=invoice.id, amount=Decimal("20.00")))
            db.commit()

            response = get_invoice(invoice.id, db=db, auth=None)

        self.assertEqual(len(response.applied_credits), 1)
        self.assertEqual(response.applied_credits[0]["credit_memo_id"], memo.id)
        self.assertEqual(response.applied_credits[0]["credit_memo_number"], "CM-2011")
        self.assertEqual(Decimal(str(response.applied_credits[0]["amount"])), Decimal("20.00"))


if __name__ == "__main__":
    unittest.main()

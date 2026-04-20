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


class SearchAndSerializerRegressionTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_unified_search_returns_estimates_customers_and_credit_notes(self):
        from app.models.contacts import Customer
        from app.models.credit_memos import CreditMemo, CreditMemoStatus
        from app.models.estimates import Estimate, EstimateStatus
        from app.routes.search import unified_search

        with self.Session() as db:
            customer = Customer(name="Aroha Ltd", company="Aroha Holdings", email="admin@aroha.test", is_active=True)
            db.add(customer)
            db.commit()

            estimate = Estimate(
                estimate_number="E-101",
                customer_id=customer.id,
                status=EstimateStatus.PENDING,
                date=date(2026, 4, 20),
                subtotal=Decimal("100.00"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=Decimal("100.00"),
            )
            credit_memo = CreditMemo(
                memo_number="CM-0001",
                customer_id=customer.id,
                status=CreditMemoStatus.ISSUED,
                date=date(2026, 4, 20),
                subtotal=Decimal("50.00"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=Decimal("50.00"),
                balance_remaining=Decimal("50.00"),
            )
            db.add_all([estimate, credit_memo])
            db.commit()

            estimate_results = unified_search(q="E-101", db=db, auth=True)
            customer_results = unified_search(q="Aroha", db=db, auth=True)
            credit_results = unified_search(q="CM-0001", db=db, auth=True)

        self.assertEqual(estimate_results["estimates"][0]["estimate_number"], "E-101")
        self.assertIn("E-101", estimate_results["estimates"][0]["display"])
        self.assertEqual(customer_results["customers"][0]["name"], "Aroha Ltd")
        self.assertEqual(credit_results["credit_memos"][0]["memo_number"], "CM-0001")
        self.assertIn("CM-0001", credit_results["credit_memos"][0]["display"])

    def test_invoice_and_credit_memo_helpers_build_typed_nested_responses(self):
        from app.models.contacts import Customer
        from app.models.credit_memos import CreditApplication, CreditMemo, CreditMemoStatus
        from app.models.invoices import Invoice, InvoiceStatus
        from app.routes.credit_memos import _credit_memo_response
        from app.routes.invoices import _invoice_response
        from app.schemas.credit_memos import CreditApplicationResponse
        from app.schemas.invoices import InvoiceCreditApplicationResponse

        with self.Session() as db:
            customer = Customer(name="Aroha Ltd", is_active=True)
            db.add(customer)
            db.commit()

            invoice = Invoice(
                invoice_number="1001",
                customer_id=customer.id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 20),
                subtotal=Decimal("115.00"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=Decimal("115.00"),
                amount_paid=Decimal("0"),
                balance_due=Decimal("115.00"),
            )
            credit_memo = CreditMemo(
                memo_number="CM-0001",
                customer_id=customer.id,
                status=CreditMemoStatus.ISSUED,
                date=date(2026, 4, 20),
                subtotal=Decimal("57.50"),
                tax_rate=Decimal("0"),
                tax_amount=Decimal("0"),
                total=Decimal("57.50"),
                amount_applied=Decimal("57.50"),
                balance_remaining=Decimal("0.00"),
            )
            db.add_all([invoice, credit_memo])
            db.flush()
            application = CreditApplication(credit_memo_id=credit_memo.id, invoice_id=invoice.id, amount=Decimal("57.50"))
            db.add(application)
            db.commit()
            db.refresh(invoice)
            db.refresh(credit_memo)

            invoice_resp = _invoice_response(invoice)
            credit_resp = _credit_memo_response(credit_memo)

        self.assertTrue(invoice_resp.applied_credits)
        self.assertIsInstance(invoice_resp.applied_credits[0], InvoiceCreditApplicationResponse)
        self.assertEqual(invoice_resp.applied_credits[0].credit_memo_number, "CM-0001")

        self.assertTrue(credit_resp.applications)
        self.assertIsInstance(credit_resp.applications[0], CreditApplicationResponse)
        self.assertEqual(credit_resp.applications[0].invoice_number, "1001")


if __name__ == "__main__":
    unittest.main()

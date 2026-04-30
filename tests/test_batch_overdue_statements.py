import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class BatchOverdueStatementsTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            aroha = Customer(name="Aroha Ltd", email="aroha@example.com")
            blank = Customer(name="No Email Ltd", email="")
            current = Customer(name="Current Ltd", email="current@example.com")
            db.add_all([aroha, blank, current])
            db.flush()
            db.add_all([
                Invoice(
                    invoice_number="INV-1",
                    customer_id=aroha.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 3, 1),
                    due_date=date(2026, 3, 31),
                    total=Decimal("115.00"),
                    balance_due=Decimal("115.00"),
                ),
                Invoice(
                    invoice_number="INV-2",
                    customer_id=aroha.id,
                    status=InvoiceStatus.PARTIAL,
                    date=date(2026, 3, 10),
                    due_date=date(2026, 4, 5),
                    total=Decimal("57.50"),
                    balance_due=Decimal("17.50"),
                ),
                Invoice(
                    invoice_number="INV-3",
                    customer_id=blank.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 3, 1),
                    due_date=date(2026, 3, 25),
                    total=Decimal("50.00"),
                    balance_due=Decimal("50.00"),
                ),
                Invoice(
                    invoice_number="INV-4",
                    customer_id=current.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 10),
                    due_date=date(2026, 4, 30),
                    total=Decimal("90.00"),
                    balance_due=Decimal("90.00"),
                ),
            ])
            db.commit()
            self.aroha_id = aroha.id

    def test_candidates_include_only_overdue_customers_with_email(self):
        from app.routes.reports import overdue_statement_candidates

        with self.Session() as db:
            payload = overdue_statement_candidates(as_of_date=date(2026, 4, 18), db=db, auth={"user_id": 1})

        self.assertEqual(payload["as_of_date"], "2026-04-18")
        self.assertEqual(len(payload["items"]), 1)
        item = payload["items"][0]
        self.assertEqual(item["customer_name"], "Aroha Ltd")
        self.assertEqual(item["overdue_invoice_count"], 2)
        self.assertEqual(item["overdue_balance"], 132.5)
        self.assertEqual(item["recipient"], "aroha@example.com")

    def test_batch_send_returns_per_customer_results(self):
        from app.routes import reports as reports_route

        request = reports_route.BatchOverdueStatementRequest(
            as_of_date=date(2026, 4, 18),
            recipients=[
                reports_route.OverdueStatementRecipient(customer_id=self.aroha_id, recipient="aroha@example.com"),
                reports_route.OverdueStatementRecipient(customer_id=999, recipient="missing@example.com"),
            ],
        )
        with mock.patch.object(reports_route, "generate_statement_pdf", return_value=b"%PDF-statement"), \
             mock.patch.object(reports_route, "send_document_email", return_value=None):
            with self.Session() as db:
                payload = reports_route.send_overdue_statements(request, db=db, auth={"user_id": 1}, request=None)

        self.assertEqual(payload["sent_count"], 1)
        self.assertEqual(payload["skipped_count"], 1)
        self.assertEqual(payload["failed_count"], 0)
        statuses = {row["customer_id"]: row["status"] for row in payload["results"]}
        self.assertEqual(statuses[self.aroha_id], "sent")
        self.assertEqual(statuses[999], "skipped")


if __name__ == "__main__":
    unittest.main()

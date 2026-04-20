import os
import sys
import types
import unittest
from datetime import date
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class MonthlyStatementCustomerTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.contacts import Customer

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            aroha = Customer(name="Aroha Ltd", email="aroha@example.com", monthly_statements_enabled=True, balance=0)
            blank = Customer(name="No Email Ltd", email="", monthly_statements_enabled=True, balance=0)
            disabled = Customer(name="Disabled Ltd", email="disabled@example.com", monthly_statements_enabled=False, balance=0)
            db.add_all([aroha, blank, disabled])
            db.commit()
            self.aroha_id = aroha.id
            self.blank_id = blank.id

    def test_candidates_include_flagged_customers_even_at_zero_balance(self):
        from app.routes.reports import monthly_statement_candidates

        with self.Session() as db:
            payload = monthly_statement_candidates(as_of_date=date(2026, 4, 30), db=db, auth={"user_id": 1})

        self.assertEqual(payload["as_of_date"], "2026-04-30")
        self.assertEqual([item["customer_name"] for item in payload["items"]], ["Aroha Ltd", "No Email Ltd"])
        self.assertEqual(payload["items"][0]["statement_balance"], 0.0)

    def test_batch_send_skips_missing_email_and_sends_flagged_customer(self):
        from app.routes import reports as reports_route

        request = reports_route.BatchMonthlyStatementRequest(
            as_of_date=date(2026, 4, 30),
            recipients=[
                reports_route.MonthlyStatementRecipient(customer_id=self.aroha_id, recipient="aroha@example.com"),
                reports_route.MonthlyStatementRecipient(customer_id=self.blank_id, recipient=""),
            ],
        )
        with mock.patch.object(reports_route, "generate_statement_pdf", return_value=b"%PDF-statement"), \
             mock.patch.object(reports_route, "send_document_email", return_value=None):
            with self.Session() as db:
                payload = reports_route.send_monthly_statements(request, db=db, auth={"user_id": 1}, request=None)

        self.assertEqual(payload["sent_count"], 1)
        self.assertEqual(payload["skipped_count"], 1)
        statuses = {row["customer_id"]: row["status"] for row in payload["results"]}
        self.assertEqual(statuses[self.aroha_id], "sent")
        self.assertEqual(statuses[self.blank_id], "skipped")

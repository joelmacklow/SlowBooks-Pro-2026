import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class FrozenDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 4, 21)


class InvoiceListMetadataTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.contacts import Customer
        from app.models.invoice_reminders import InvoiceReminderAudit, InvoiceReminderRule
        from app.models.invoices import Invoice, InvoiceStatus

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            enabled = Customer(name="Enabled Ltd", email="enabled@example.com", invoice_reminders_enabled=True)
            disabled = Customer(name="Disabled Ltd", email="disabled@example.com", invoice_reminders_enabled=False)
            db.add_all([enabled, disabled])
            db.flush()

            rule = InvoiceReminderRule(
                name="3 days overdue",
                timing_direction="after_due",
                day_offset=3,
                is_enabled=True,
                sort_order=0,
                subject_template="Reminder",
                body_template="Body",
            )
            db.add(rule)
            db.flush()

            inv_enabled = Invoice(
                invoice_number="INV-1001",
                customer_id=enabled.id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 1),
                due_date=date(2026, 4, 10),
                total=Decimal("300.00"),
                amount_paid=Decimal("0.00"),
                balance_due=Decimal("300.00"),
            )
            inv_disabled = Invoice(
                invoice_number="INV-1002",
                customer_id=disabled.id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 5),
                due_date=date(2026, 4, 8),
                total=Decimal("80.00"),
                amount_paid=Decimal("0.00"),
                balance_due=Decimal("80.00"),
            )
            db.add_all([inv_enabled, inv_disabled])
            db.flush()

            db.add_all([
                InvoiceReminderAudit(
                    invoice_id=inv_enabled.id,
                    customer_id=enabled.id,
                    rule_id=rule.id,
                    recipient=enabled.email,
                    status="sent",
                    trigger_type="automatic",
                    scheduled_for_date=date(2026, 4, 13),
                    days_from_due_snapshot=3,
                    balance_due_snapshot=Decimal("300.00"),
                ),
                InvoiceReminderAudit(
                    invoice_id=inv_enabled.id,
                    customer_id=enabled.id,
                    rule_id=rule.id,
                    recipient=enabled.email,
                    status="sent",
                    trigger_type="manual",
                    scheduled_for_date=date(2026, 4, 20),
                    days_from_due_snapshot=10,
                    balance_due_snapshot=Decimal("300.00"),
                ),
            ])
            db.commit()

    def test_list_invoices_includes_reminder_summary_fields(self):
        from app.routes.invoices import list_invoices

        with mock.patch("app.routes.invoices.date", FrozenDate):
            with self.Session() as db:
                invoices = list_invoices(db=db, auth=SimpleNamespace())

        rows = {invoice.invoice_number: invoice for invoice in invoices}
        self.assertEqual(rows["INV-1001"].reminder_count, 2)
        self.assertEqual(rows["INV-1001"].reminder_summary, "2 sent")
        self.assertTrue(rows["INV-1001"].invoice_reminders_enabled)
        self.assertEqual(rows["INV-1002"].reminder_summary, "Turned off")
        self.assertFalse(rows["INV-1002"].invoice_reminders_enabled)


if __name__ == "__main__":
    unittest.main()

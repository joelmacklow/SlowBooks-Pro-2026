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


class RecurringScheduleUpdateTests(unittest.TestCase):
    def setUp(self):
        from app.models import Customer, GstCode, Item, RecurringInvoice, RecurringInvoiceLine  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_update_recurring_accepts_start_date_and_recalculates_next_due(self):
        from app.models.contacts import Customer
        from app.models.recurring import RecurringInvoice
        from app.routes.recurring import update_recurring
        from app.schemas.recurring import RecurringLineCreate, RecurringUpdate
        from app.services.recurring_service import calculate_next_due

        with self.Session() as db:
            customer = Customer(name="Aroha Ltd")
            replacement = Customer(name="Harbour Supplies")
            db.add_all([customer, replacement])
            db.commit()

            recurring = RecurringInvoice(
                customer_id=customer.id,
                frequency="monthly",
                start_date=date(2026, 4, 1),
                next_due=date(2026, 5, 1),
                terms="Net 30",
                tax_rate=Decimal("0.15"),
                notes="Recurring",
                invoices_created=3,
            )
            db.add(recurring)
            db.commit()

            updated = update_recurring(
                recurring.id,
                RecurringUpdate(
                    customer_id=replacement.id,
                    start_date=date(2026, 4, 8),
                    frequency="weekly",
                    terms="Due 1st of next month",
                    lines=[RecurringLineCreate(description="Pens", quantity=2, rate=50, gst_code="GST15")],
                ),
                db=db,
                auth=None,
            )
            stored = db.query(RecurringInvoice).filter(RecurringInvoice.id == recurring.id).one()

        self.assertEqual(updated.customer_id, replacement.id)
        self.assertEqual(stored.customer_id, replacement.id)
        self.assertEqual(stored.start_date, date(2026, 4, 8))
        self.assertEqual(stored.frequency, "weekly")
        self.assertEqual(stored.terms, "Due 1st of next month")
        self.assertEqual(stored.next_due, calculate_next_due(date(2026, 4, 8), "weekly"))


if __name__ == "__main__":
    unittest.main()

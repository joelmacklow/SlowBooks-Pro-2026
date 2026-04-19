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


class InvoiceReminderFoundationTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus
        from app.models.settings import Settings

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            db.add_all([
                Settings(key="company_name", value="SlowBooks NZ"),
                Settings(key="locale", value="en-NZ"),
                Settings(key="currency", value="NZD"),
            ])
            aroha = Customer(name="Aroha Ltd", email="aroha@example.com")
            disabled = Customer(name="Disabled Ltd", email="disabled@example.com", invoice_reminders_enabled=False)
            no_email = Customer(name="No Email Ltd", email="")
            db.add_all([aroha, disabled, no_email])
            db.flush()

            db.add_all([
                Invoice(
                    invoice_number="INV-BEFORE",
                    customer_id=aroha.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 22),
                    total=Decimal("115.00"),
                    balance_due=Decimal("115.00"),
                ),
                Invoice(
                    invoice_number="INV-AFTER",
                    customer_id=aroha.id,
                    status=InvoiceStatus.PARTIAL,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 12),
                    total=Decimal("200.00"),
                    balance_due=Decimal("80.00"),
                ),
                Invoice(
                    invoice_number="INV-DISABLED",
                    customer_id=disabled.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 12),
                    total=Decimal("90.00"),
                    balance_due=Decimal("90.00"),
                ),
                Invoice(
                    invoice_number="INV-NOEMAIL",
                    customer_id=no_email.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 12),
                    total=Decimal("60.00"),
                    balance_due=Decimal("60.00"),
                ),
                Invoice(
                    invoice_number="INV-CURRENT",
                    customer_id=aroha.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 19),
                    total=Decimal("40.00"),
                    balance_due=Decimal("40.00"),
                ),
            ])
            db.commit()
            self.aroha_id = aroha.id

    def test_default_rules_are_seeded_with_expected_order_and_copy(self):
        from app.routes import settings as settings_route

        with self.Session() as db:
            rules = settings_route.list_invoice_reminder_rules(db=db, auth={"user_id": 1})

        self.assertEqual([(rule.timing_direction, rule.day_offset) for rule in rules], [
            ("before_due", 3),
            ("after_due", 3),
            ("after_due", 5),
            ("after_due", 7),
            ("after_due", 10),
            ("after_due", 15),
        ])
        self.assertEqual(rules[0].subject_template, "Upcoming due date for invoice {{ invoice_number }}")
        self.assertIn("courtesy reminder", rules[0].body_template.lower())
        self.assertIn("friendly reminder", rules[1].subject_template.lower())
        self.assertIn("urgent attention", rules[4].subject_template.lower())
        self.assertIn("final reminder", rules[5].subject_template.lower())

    def test_preview_uses_default_rules_for_before_and_after_due_matches(self):
        from app.routes import reports as reports_route

        with self.Session() as db:
            preview = reports_route.invoice_reminder_preview(
                as_of_date=date(2026, 4, 19),
                db=db,
                auth={"user_id": 1},
            )

        self.assertEqual(preview["item_count"], 2)
        by_number = {row["invoice_number"]: row for row in preview["items"]}
        self.assertEqual(by_number["INV-BEFORE"]["timing_direction"], "before_due")
        self.assertEqual(by_number["INV-BEFORE"]["day_offset"], 3)
        self.assertEqual(by_number["INV-BEFORE"]["days_from_due"], -3)
        self.assertEqual(by_number["INV-AFTER"]["timing_direction"], "after_due")
        self.assertEqual(by_number["INV-AFTER"]["day_offset"], 7)
        self.assertEqual(by_number["INV-AFTER"]["days_from_due"], 7)

    def test_preview_excludes_customers_without_email_or_disabled_reminders(self):
        from app.routes import reports as reports_route

        with self.Session() as db:
            preview = reports_route.invoice_reminder_preview(
                as_of_date=date(2026, 4, 15),
                db=db,
                auth={"user_id": 1},
            )

        invoice_numbers = {row["invoice_number"] for row in preview["items"]}
        self.assertEqual(invoice_numbers, {"INV-AFTER"})

    def test_preview_includes_latest_audit_metadata(self):
        from app.models.invoice_reminders import InvoiceReminderAudit, InvoiceReminderRule
        from app.models.invoices import Invoice
        from app.routes import reports as reports_route
        from app.routes import settings as settings_route

        with self.Session() as db:
            settings_route.list_invoice_reminder_rules(db=db, auth={"user_id": 1})
            rule = db.query(InvoiceReminderRule).filter(
                InvoiceReminderRule.timing_direction == "after_due",
                InvoiceReminderRule.day_offset == 7,
            ).one()
            invoice = db.query(Invoice).filter(Invoice.invoice_number == "INV-AFTER").one()
            db.add(InvoiceReminderAudit(
                invoice_id=invoice.id,
                customer_id=self.aroha_id,
                rule_id=rule.id,
                email_log_id=None,
                recipient="aroha@example.com",
                status="failed",
                trigger_type="manual",
                scheduled_for_date=date(2026, 4, 19),
                days_from_due_snapshot=7,
                balance_due_snapshot=Decimal("80.00"),
                detail="Mailbox full",
            ))
            db.commit()

            preview = reports_route.invoice_reminder_preview(
                as_of_date=date(2026, 4, 19),
                db=db,
                auth={"user_id": 1},
            )

        row = next(item for item in preview["items"] if item["invoice_number"] == "INV-AFTER")
        self.assertEqual(row["last_reminder_status"], "failed")
        self.assertEqual(row["last_reminder_trigger_type"], "manual")
        self.assertEqual(row["last_reminder_detail"], "Mailbox full")
        self.assertIsNotNone(row["last_reminder_sent_at"])

    def test_custom_rule_crud_still_works_alongside_default_rules(self):
        from app.routes import settings as settings_route

        with self.Session() as db:
            settings_route.list_invoice_reminder_rules(db=db, auth={"user_id": 1})
            created = settings_route.create_invoice_reminder_rule(
                settings_route.InvoiceReminderRuleCreate(
                    timing_direction="before_due",
                    day_offset=1,
                    sort_order=6,
                    name="1 day before due",
                ),
                db=db,
                auth={"user_id": 1},
            )
            updated = settings_route.update_invoice_reminder_rule(
                created.id,
                settings_route.InvoiceReminderRuleUpdate(
                    timing_direction="after_due",
                    day_offset=20,
                    is_enabled=False,
                ),
                db=db,
                auth={"user_id": 1},
            )

        self.assertEqual(updated.timing_direction, "after_due")
        self.assertEqual(updated.day_offset, 20)
        self.assertFalse(updated.is_enabled)
        self.assertEqual(updated.name, "20 days overdue")

    def test_customer_routes_persist_invoice_reminder_flag(self):
        from app.routes import customers as customers_route

        with self.Session() as db:
            created = customers_route.create_customer(
                customers_route.CustomerCreate(
                    name="Reminder Off Co",
                    email="contact@example.com",
                    invoice_reminders_enabled=False,
                ),
                db=db,
                auth={"user_id": 1},
            )
            self.assertFalse(created.invoice_reminders_enabled)

            updated = customers_route.update_customer(
                created.id,
                customers_route.CustomerUpdate(invoice_reminders_enabled=True),
                db=db,
                auth={"user_id": 1},
            )
            self.assertTrue(updated.invoice_reminders_enabled)


if __name__ == "__main__":
    unittest.main()

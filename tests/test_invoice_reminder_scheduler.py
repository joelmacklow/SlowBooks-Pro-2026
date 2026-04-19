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


class FakeSMTP:
    sent_messages = []
    instances = []
    fail_send = False

    def __init__(self, host, port, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.quit_called = False
        self.__class__.instances.append(self)

    def starttls(self):
        return None

    def login(self, user, password):
        return None

    def sendmail(self, from_email, recipients, message):
        if self.__class__.fail_send:
            raise RuntimeError('smtp down')
        self.__class__.sent_messages.append({
            'from_email': from_email,
            'recipients': recipients,
            'message': message,
        })

    def quit(self):
        self.quit_called = True
        return None


class InvoiceReminderSchedulerTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus
        from app.models.settings import Settings
        from app.services import email_service
        from app.services import invoice_reminders as reminder_service
        from app.services import invoice_reminder_scheduler as scheduler_service

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.scheduler_service = scheduler_service
        self.reminder_service = reminder_service
        self.email_service = email_service
        self.original_smtp = email_service.smtplib.SMTP
        self.original_password = email_service.SMTP_PASSWORD
        self.original_session_local = scheduler_service.SessionLocal
        self.original_generate_invoice_pdf = reminder_service.generate_invoice_pdf

        email_service.smtplib.SMTP = FakeSMTP
        email_service.SMTP_PASSWORD = "env-secret"
        scheduler_service.SessionLocal = self.Session
        reminder_service.generate_invoice_pdf = lambda *_args, **_kwargs: b"%PDF-invoice"
        FakeSMTP.sent_messages = []
        FakeSMTP.instances = []
        FakeSMTP.fail_send = False

        with self.Session() as db:
            for key, value in {
                "company_name": "SlowBooks NZ",
                "company_email": "accounts@example.com",
                "locale": "en-NZ",
                "currency": "NZD",
                "smtp_host": "smtp.example.com",
                "smtp_port": "587",
                "smtp_user": "mailer@example.com",
                "smtp_from_email": "accounts@example.com",
                "smtp_from_name": "SlowBooks NZ",
                "smtp_use_tls": "true",
                "invoice_reminder_scheduler_enabled": "true",
                "invoice_reminder_scheduler_interval_minutes": "15",
            }.items():
                db.add(Settings(key=key, value=value))
            customer = Customer(name="Aroha Ltd", email="aroha@example.com")
            db.add(customer)
            db.flush()
            db.add_all([
                Invoice(
                    invoice_number="INV-BEFORE",
                    customer_id=customer.id,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 22),
                    total=Decimal("115.00"),
                    balance_due=Decimal("115.00"),
                ),
                Invoice(
                    invoice_number="INV-AFTER",
                    customer_id=customer.id,
                    status=InvoiceStatus.PARTIAL,
                    date=date(2026, 4, 1),
                    due_date=date(2026, 4, 12),
                    total=Decimal("80.00"),
                    balance_due=Decimal("80.00"),
                ),
            ])
            db.commit()

    def tearDown(self):
        self.email_service.smtplib.SMTP = self.original_smtp
        self.email_service.SMTP_PASSWORD = self.original_password
        self.scheduler_service.SessionLocal = self.original_session_local
        self.reminder_service.generate_invoice_pdf = self.original_generate_invoice_pdf

    def test_run_invoice_reminder_cycle_sends_due_reminders_and_records_status(self):
        from app.models.email_log import EmailLog
        from app.models.invoice_reminders import InvoiceReminderAudit
        from app.services.invoice_reminders import get_scheduler_state

        summary = self.scheduler_service.run_invoice_reminder_cycle(as_of_date=date(2026, 4, 19))
        self.assertEqual(summary["sent_count"], 2)
        self.assertEqual(summary["failed_count"], 0)
        self.assertEqual(summary["duplicate_count"], 0)

        with self.Session() as db:
            self.assertEqual(db.query(EmailLog).filter(EmailLog.entity_type == "invoice_reminder").count(), 2)
            audits = db.query(InvoiceReminderAudit).order_by(InvoiceReminderAudit.id).all()
            self.assertEqual(len(audits), 2)
            self.assertTrue(all(audit.email_log_id for audit in audits))
            state = get_scheduler_state(db)
            self.assertEqual(state["last_run_status"], "ok")
            self.assertIn('"sent_count": 2', state["last_run_summary"])

    def test_run_invoice_reminder_cycle_prevents_duplicates_for_same_invoice_rule_date(self):
        from app.models.email_log import EmailLog
        from app.models.invoice_reminders import InvoiceReminderAudit

        first = self.scheduler_service.run_invoice_reminder_cycle(as_of_date=date(2026, 4, 19))
        second = self.scheduler_service.run_invoice_reminder_cycle(as_of_date=date(2026, 4, 19))
        self.assertEqual(first["sent_count"], 2)
        self.assertEqual(second["duplicate_count"], 2)
        self.assertEqual(second["sent_count"], 0)

        with self.Session() as db:
            self.assertEqual(db.query(EmailLog).filter(EmailLog.entity_type == "invoice_reminder").count(), 2)
            self.assertEqual(db.query(InvoiceReminderAudit).count(), 2)

    def test_run_invoice_reminder_cycle_honors_disabled_scheduler_setting(self):
        from app.models.email_log import EmailLog
        from app.models.settings import Settings
        from app.services.invoice_reminders import get_scheduler_state

        with self.Session() as db:
            db.query(Settings).filter(Settings.key == "invoice_reminder_scheduler_enabled").one().value = "false"
            db.commit()

        summary = self.scheduler_service.run_invoice_reminder_cycle(as_of_date=date(2026, 4, 19))
        self.assertEqual(summary["status"], "disabled")

        with self.Session() as db:
            self.assertEqual(db.query(EmailLog).count(), 0)
            state = get_scheduler_state(db)
            self.assertEqual(state["last_run_status"], "disabled")

    def test_run_invoice_reminder_cycle_records_failure_without_duplicate_retries(self):
        from app.models.email_log import EmailLog
        from app.models.invoice_reminders import InvoiceReminderAudit

        FakeSMTP.fail_send = True
        first = self.scheduler_service.run_invoice_reminder_cycle(as_of_date=date(2026, 4, 19))
        second = self.scheduler_service.run_invoice_reminder_cycle(as_of_date=date(2026, 4, 19))
        self.assertEqual(first["failed_count"], 2)
        self.assertEqual(second["duplicate_count"], 2)

        with self.Session() as db:
            self.assertEqual(db.query(EmailLog).filter(EmailLog.entity_type == "invoice_reminder").count(), 2)
            audits = db.query(InvoiceReminderAudit).all()
            self.assertEqual(len(audits), 2)
            self.assertTrue(all(audit.status == "failed" for audit in audits))

    def test_build_scheduler_handles_pending_job_without_next_run_time_attribute(self):
        scheduler = self.scheduler_service.build_invoice_reminder_scheduler()
        try:
            job = scheduler.get_job(self.scheduler_service.JOB_ID)
            self.assertIsNotNone(job)
            self.assertEqual(self.scheduler_service._job_next_run_iso(job), '')
        finally:
            if getattr(scheduler, 'running', False):
                scheduler.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()

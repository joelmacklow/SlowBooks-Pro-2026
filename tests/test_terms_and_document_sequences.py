import os
import sys
import types
import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class TermsAndDocumentSequencesTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_payment_terms_support_custom_next_month_due_dates(self):
        from app.services.payment_terms import parse_payment_terms_config, resolve_due_date_for_terms

        config = "Net 30|net:30\nDue 1st of next month|next_month_day:1\nDue on Receipt|days:0"
        parsed = parse_payment_terms_config(config)

        self.assertEqual([entry["label"] for entry in parsed], ["Net 30", "Due 1st of next month", "Due on Receipt"])
        self.assertEqual(resolve_due_date_for_terms(date(2026, 4, 20), "Due 1st of next month", config), date(2026, 5, 1))
        self.assertEqual(resolve_due_date_for_terms(date(2026, 4, 20), "Due on Receipt", config), date(2026, 4, 20))

    def test_document_sequences_use_settings_prefixes_and_next_numbers(self):
        from app.models.credit_memos import CreditMemo
        from app.models.purchase_orders import PurchaseOrder
        from app.services.document_sequences import allocate_document_number

        with self.Session() as db:
            first_cm = allocate_document_number(
                db,
                model=CreditMemo,
                field_name="memo_number",
                prefix_key="credit_memo_prefix",
                next_key="credit_memo_next_number",
                default_prefix="CM-",
                default_next_number="0001",
            )
            first_po = allocate_document_number(
                db,
                model=PurchaseOrder,
                field_name="po_number",
                prefix_key="purchase_order_prefix",
                next_key="purchase_order_next_number",
                default_prefix="PO-",
                default_next_number="0001",
            )

        self.assertEqual(first_cm, "CM-0001")
        self.assertEqual(first_po, "PO-0001")

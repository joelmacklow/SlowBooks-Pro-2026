import os
import sys
import types
import unittest
from pathlib import Path
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


FIXTURE_DIR = Path(__file__).with_name('fixtures')
SAMPLE_STATEMENT = FIXTURE_DIR / 'anz_unreconciled_reconciliation_sample.csv'


class BankImportCsvTests(unittest.TestCase):
    def setUp(self):
        from app.models import (  # noqa: F401
            Account, BankAccount, BankTransaction, Bill, BillLine, BillPayment, BillPaymentAllocation,
            CreditApplication, CreditMemo, CreditMemoLine, Customer, Estimate, EstimateLine, GstCode,
            Invoice, InvoiceLine, Item, Payment, PaymentAllocation, Reconciliation, Settings,
            Transaction, TransactionLine, Vendor,
        )

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_parse_statement_file_reads_anz_csv_reference_and_code(self):
        from app.services.ofx_import import parse_statement_file

        content = b"Type,Details,Particulars,Code,Reference,Amount,Date,ForeignCurrencyAmount,ConversionCharge\nBill Payment,Learn Innovatio,Learning Inn,,Inv 8746,53.91,16/04/2026,,\nPayment,Nazarene,Nazarene,Wages,,-461.25,15/04/2026,,\n"
        parsed = parse_statement_file(content, filename="statement.csv")

        self.assertEqual(parsed["format"], "csv")
        self.assertEqual(len(parsed["transactions"]), 2)
        self.assertEqual(parsed["transactions"][0]["reference"], "Inv 8746")
        self.assertIsNone(parsed["transactions"][0]["code"])
        self.assertEqual(parsed["transactions"][1]["code"], "Wages")
        self.assertEqual(parsed["transactions"][1]["amount"], Decimal("-461.25"))

    def test_fixture_statement_file_covers_seeded_unreconciled_invoice_and_bill_matches(self):
        from app.services.ofx_import import parse_statement_file

        parsed = parse_statement_file(SAMPLE_STATEMENT.read_bytes(), filename=SAMPLE_STATEMENT.name)

        self.assertEqual(parsed["format"], "csv")
        self.assertEqual(len(parsed["transactions"]), 5)
        self.assertEqual(parsed["transactions"][0]["reference"], "INV-2001")
        self.assertEqual(parsed["transactions"][0]["amount"], Decimal("1422.00"))
        self.assertEqual(parsed["transactions"][3]["reference"], "B-3004")
        self.assertEqual(parsed["transactions"][3]["code"], "Cleaning")
        self.assertEqual(parsed["transactions"][4]["amount"], Decimal("-287.50"))

    def test_fixture_rows_reference_only_open_seed_documents(self):
        import scripts.seed_database as seed_database
        import scripts.seed_irs_mock_data as seed_demo
        from app.models.bills import Bill, BillStatus
        from app.models.invoices import Invoice, InvoiceStatus
        from app.services.ofx_import import parse_statement_file

        seed_database.SessionLocal = self.Session
        seed_demo.SessionLocal = self.Session

        seed_database.seed()
        seed_demo.seed()

        parsed = parse_statement_file(SAMPLE_STATEMENT.read_bytes(), filename=SAMPLE_STATEMENT.name)
        fixture_refs = {txn["reference"] for txn in parsed["transactions"]}

        with self.Session() as db:
            open_invoices = {
                f"INV-{invoice.invoice_number}"
                for invoice in db.query(Invoice).filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL])).all()
            }
            open_bills = {
                f"B-{bill.bill_number}"
                for bill in db.query(Bill).filter(Bill.status.in_([BillStatus.UNPAID, BillStatus.PARTIAL])).all()
            }

        self.assertEqual(fixture_refs, {"INV-2001", "INV-2004", "INV-2006", "B-3004", "B-3005"})
        self.assertTrue(fixture_refs.issubset(open_invoices | open_bills))

    def test_import_transactions_stores_reference_and_code_and_skips_duplicates(self):
        from app.models.accounts import Account, AccountType
        from app.models.banking import BankAccount, BankTransaction
        from app.services.ofx_import import import_transactions, parse_statement_file, statement_summary

        content = b"Type,Details,Particulars,Code,Reference,Amount,Date,ForeignCurrencyAmount,ConversionCharge\nDirect Credit,John Bates Wheel Ali,John Bates,Wheel Align,8757+8749,3173.86,10/04/2026,,\n"
        parsed = parse_statement_file(content, filename="statement.csv")

        with self.Session() as db:
            account = Account(name="Business Bank Account", account_number="090", account_type=AccountType.ASSET, is_active=True)
            db.add(account)
            db.commit()
            bank_account = BankAccount(name="ANZ", account_id=account.id, bank_name="ANZ", last_four="1208", balance=Decimal("0.00"), is_active=True)
            db.add(bank_account)
            db.commit()

            first = import_transactions(db, bank_account.id, parsed["transactions"], import_source=parsed["format"])
            summary = statement_summary(parsed["transactions"], ending_balance=first["ending_balance"])
            second = import_transactions(db, bank_account.id, parsed["transactions"], import_source=parsed["format"])
            txns = db.query(BankTransaction).filter(BankTransaction.bank_account_id == bank_account.id).all()
            db.refresh(bank_account)

        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].reference, "8757+8749")
        self.assertEqual(txns[0].code, "Wheel Align")
        self.assertEqual(txns[0].import_source, "csv")
        self.assertEqual(summary["statement_date"], "2026-04-10")
        self.assertEqual(summary["statement_total"], 3173.86)
        self.assertEqual(summary["statement_balance"], 3173.86)
        self.assertTrue(first["import_batch_id"])
        self.assertEqual(Decimal(str(bank_account.balance)), Decimal("3173.86"))


if __name__ == "__main__":
    unittest.main()

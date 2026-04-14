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
dateutil_stub = types.ModuleType("dateutil")
relativedelta_stub = types.ModuleType("dateutil.relativedelta")


class relativedelta:
    def __init__(self, months=0, years=0):
        self.days = (months * 31) + (years * 365)

    def __radd__(self, other):
        from datetime import timedelta

        return other + timedelta(days=self.days)


relativedelta_stub.relativedelta = relativedelta
sys.modules.setdefault("dateutil", dateutil_stub)
sys.modules.setdefault("dateutil.relativedelta", relativedelta_stub)

from app.database import Base
from app.models.accounts import Account, AccountType
from app.models.contacts import Customer, Vendor
from app.models.bills import Bill
from app.models.credit_memos import CreditMemo
from app.models.invoices import Invoice
from app.models.settings import Settings
from app.models.transactions import Transaction, TransactionLine


class DocumentGstCalculationTests(unittest.TestCase):
    def setUp(self):
        from app.models.gst import GstCode  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _seed_parties_and_accounts(self, db):
        customer = Customer(name="Aroha Ltd")
        vendor = Vendor(name="Harbour Supplies")
        db.add_all([
            customer,
            vendor,
            Account(name="Accounts Receivable", account_number="1100", account_type=AccountType.ASSET),
            Account(name="Accounts Payable", account_number="2000", account_type=AccountType.LIABILITY),
            Account(name="Sales Tax Payable", account_number="2200", account_type=AccountType.LIABILITY),
            Account(name="Service Income", account_number="4000", account_type=AccountType.INCOME),
            Account(name="Expenses", account_number="6000", account_type=AccountType.EXPENSE),
        ])
        db.commit()
        return customer, vendor

    def _set_inclusive_prices(self, db):
        db.add(Settings(key="prices_include_gst", value="true"))
        db.commit()

    def _account_snapshot(self, line):
        return line.account.account_number, line.account.name

    def test_invoice_totals_use_line_gst_codes_not_document_tax_rate(self):
        from app.routes.invoices import create_invoice
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            invoice = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                tax_rate=Decimal("0.9900"),
                lines=[
                    InvoiceLineCreate(description="Standard", quantity=1, rate=Decimal("100"), gst_code="GST15"),
                    InvoiceLineCreate(description="Zero", quantity=1, rate=Decimal("50"), gst_code="ZERO"),
                ],
            ), db=db)

        self.assertEqual(invoice.subtotal, Decimal("150.00"))
        self.assertEqual(invoice.tax_amount, Decimal("15.00"))
        self.assertEqual(invoice.total, Decimal("165.00"))
        self.assertEqual(invoice.tax_rate, Decimal("0.1000"))

    def test_estimate_po_credit_and_recurring_totals_use_line_gst_codes(self):
        from app.routes.credit_memos import create_credit_memo
        from app.routes.estimates import create_estimate
        from app.routes.purchase_orders import create_po
        from app.routes.recurring import create_recurring
        from app.schemas.credit_memos import CreditMemoCreate, CreditMemoLineCreate
        from app.schemas.estimates import EstimateCreate, EstimateLineCreate
        from app.schemas.purchase_orders import POCreate, POLineCreate
        from app.schemas.recurring import RecurringCreate, RecurringLineCreate
        from app.services.recurring_service import generate_due_invoices

        with self.Session() as db:
            customer, vendor = self._seed_parties_and_accounts(db)
            estimate = create_estimate(EstimateCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                tax_rate=Decimal("0.9900"),
                lines=[EstimateLineCreate(description="Estimate", quantity=1, rate=Decimal("100"), gst_code="ZERO")],
            ), db=db)
            po = create_po(POCreate(
                vendor_id=vendor.id,
                date=date(2026, 4, 13),
                tax_rate=0.99,
                lines=[POLineCreate(description="PO", quantity=1, rate=100, gst_code="EXEMPT")],
            ), db=db)
            credit = create_credit_memo(CreditMemoCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                tax_rate=0.99,
                lines=[CreditMemoLineCreate(description="Credit", quantity=1, rate=100, gst_code="NO_GST")],
            ), db=db)
            create_recurring(RecurringCreate(
                customer_id=customer.id,
                frequency="monthly",
                start_date=date(2026, 4, 13),
                tax_rate=0.99,
                lines=[RecurringLineCreate(description="Recurring", quantity=1, rate=100, gst_code="ZERO")],
            ), db=db)
            generated_ids = generate_due_invoices(db, as_of=date(2026, 4, 13))
            generated_invoice = db.query(Invoice).filter(Invoice.id == generated_ids[0]).one()

        self.assertEqual(estimate.tax_amount, Decimal("0.00"))
        self.assertEqual(estimate.total, Decimal("100.00"))
        self.assertEqual(Decimal(str(po.tax_amount)), Decimal("0.00"))
        self.assertEqual(Decimal(str(po.total)), Decimal("100.00"))
        self.assertEqual(Decimal(str(credit.tax_amount)), Decimal("0.00"))
        self.assertEqual(Decimal(str(credit.total)), Decimal("100.00"))
        self.assertEqual(generated_invoice.tax_amount, Decimal("0.00"))
        self.assertEqual(generated_invoice.total, Decimal("100.00"))

    def test_inclusive_invoice_posts_balanced_net_income_and_gst(self):
        from app.routes.invoices import create_invoice
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            self._set_inclusive_prices(db)
            invoice = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[InvoiceLineCreate(description="Inclusive", quantity=1, rate=Decimal("115"), gst_code="GST15")],
            ), db=db)
            stored_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).one()
            lines = db.query(TransactionLine).filter(TransactionLine.transaction_id == stored_invoice.transaction_id).all()
            gst_line = next(line for line in lines if line.credit == Decimal("15.00"))
            gst_account_number, gst_account_name = self._account_snapshot(gst_line)
            gst_description = gst_line.description

        self.assertEqual(invoice.subtotal, Decimal("100.00"))
        self.assertEqual(invoice.tax_amount, Decimal("15.00"))
        self.assertEqual(invoice.total, Decimal("115.00"))
        self.assertEqual(sum(line.debit for line in lines), Decimal("115.00"))
        self.assertEqual(sum(line.credit for line in lines), Decimal("115.00"))
        self.assertEqual(
            sorted(line.credit for line in lines if line.credit > 0),
            [Decimal("15.00"), Decimal("100.00")],
        )
        self.assertEqual(gst_account_number, "2200")
        self.assertEqual(gst_account_name, "GST")
        self.assertEqual(gst_description, "GST")

    def test_inclusive_bill_posts_balanced_net_expense_and_input_gst(self):
        from app.routes.bills import create_bill
        from app.schemas.bills import BillCreate, BillLineCreate

        with self.Session() as db:
            _customer, vendor = self._seed_parties_and_accounts(db)
            self._set_inclusive_prices(db)
            bill = create_bill(BillCreate(
                vendor_id=vendor.id,
                bill_number="B-1",
                date=date(2026, 4, 13),
                lines=[BillLineCreate(description="Inclusive", quantity=1, rate=115, gst_code="GST15")],
            ), db=db)
            stored_bill = db.query(Bill).filter(Bill.id == bill.id).one()
            lines = db.query(TransactionLine).filter(TransactionLine.transaction_id == stored_bill.transaction_id).all()
            gst_line = next(line for line in lines if line.debit == Decimal("15.00"))
            gst_account_number, gst_account_name = self._account_snapshot(gst_line)
            gst_description = gst_line.description

        self.assertEqual(Decimal(str(bill.subtotal)), Decimal("100.00"))
        self.assertEqual(Decimal(str(bill.tax_amount)), Decimal("15.00"))
        self.assertEqual(Decimal(str(bill.total)), Decimal("115.00"))
        self.assertEqual(sum(line.debit for line in lines), Decimal("115.00"))
        self.assertEqual(sum(line.credit for line in lines), Decimal("115.00"))
        self.assertEqual(
            sorted(line.debit for line in lines if line.debit > 0),
            [Decimal("15.00"), Decimal("100.00")],
        )
        self.assertEqual(gst_account_number, "2200")
        self.assertEqual(gst_account_name, "GST")
        self.assertEqual(gst_description, "GST on bill")

    def test_credit_memo_posts_gst_debit_to_gst_account(self):
        from app.routes.credit_memos import create_credit_memo
        from app.schemas.credit_memos import CreditMemoCreate, CreditMemoLineCreate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            credit = create_credit_memo(CreditMemoCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[CreditMemoLineCreate(description="Credit", quantity=1, rate=100, gst_code="GST15")],
            ), db=db)
            stored_credit = db.query(CreditMemo).filter(CreditMemo.id == credit.id).one()
            lines = db.query(TransactionLine).filter(TransactionLine.transaction_id == stored_credit.transaction_id).all()
            gst_line = next(line for line in lines if line.debit == Decimal("15.00"))
            gst_account_number, gst_account_name = self._account_snapshot(gst_line)
            gst_description = gst_line.description

        self.assertEqual(sum(line.debit for line in lines), Decimal("115.00"))
        self.assertEqual(sum(line.credit for line in lines), Decimal("115.00"))
        self.assertEqual(gst_account_number, "2200")
        self.assertEqual(gst_account_name, "GST")
        self.assertEqual(gst_description, "GST credit")

    def test_generated_recurring_invoice_posts_gst_credit_to_gst_account(self):
        from app.routes.recurring import create_recurring
        from app.schemas.recurring import RecurringCreate, RecurringLineCreate
        from app.services.recurring_service import generate_due_invoices

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            create_recurring(RecurringCreate(
                customer_id=customer.id,
                frequency="monthly",
                start_date=date(2026, 4, 13),
                lines=[RecurringLineCreate(description="Recurring", quantity=1, rate=100, gst_code="GST15")],
            ), db=db)
            generated_ids = generate_due_invoices(db, as_of=date(2026, 4, 13))
            generated_invoice = db.query(Invoice).filter(Invoice.id == generated_ids[0]).one()
            lines = db.query(TransactionLine).filter(TransactionLine.transaction_id == generated_invoice.transaction_id).all()
            gst_line = next(line for line in lines if line.credit == Decimal("15.00"))
            gst_account_number, gst_account_name = self._account_snapshot(gst_line)
            gst_description = gst_line.description

        self.assertEqual(sum(line.debit for line in lines), Decimal("115.00"))
        self.assertEqual(sum(line.credit for line in lines), Decimal("115.00"))
        self.assertEqual(gst_account_number, "2200")
        self.assertEqual(gst_account_name, "GST")
        self.assertEqual(gst_description, "GST")

    def test_invoice_line_update_reverses_old_journal_and_posts_replacement(self):
        from app.routes.invoices import create_invoice, update_invoice
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate, InvoiceUpdate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            created = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[InvoiceLineCreate(description="Original", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            original_transaction_id = db.query(Invoice).filter(Invoice.id == created.id).one().transaction_id

            updated = update_invoice(created.id, InvoiceUpdate(
                lines=[InvoiceLineCreate(description="Replacement", quantity=1, rate=Decimal("200"), gst_code="GST15")],
            ), db=db)
            stored_invoice = db.query(Invoice).filter(Invoice.id == created.id).one()
            ar_account = db.query(Account).filter(Account.account_number == "1100").one()
            gst_account = db.query(Account).filter(Account.account_number == "2200").one()
            income_account = db.query(Account).filter(Account.account_number == "4000").one()
            transactions = db.query(Transaction).filter(Transaction.source_id == created.id).order_by(Transaction.id).all()

        self.assertEqual(updated.subtotal, Decimal("200.00"))
        self.assertEqual(updated.tax_amount, Decimal("30.00"))
        self.assertEqual(updated.total, Decimal("230.00"))
        self.assertNotEqual(stored_invoice.transaction_id, original_transaction_id)
        self.assertEqual(
            [txn.source_type for txn in transactions],
            ["invoice", "invoice_reversal", "invoice"],
        )
        self.assertEqual(ar_account.balance, Decimal("230.00"))
        self.assertEqual(gst_account.balance, Decimal("30.00"))
        self.assertEqual(income_account.balance, Decimal("200.00"))

    def test_duplicate_invoice_posts_a_new_journal_entry(self):
        from app.routes.invoices import create_invoice, duplicate_invoice
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            created = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[InvoiceLineCreate(description="Duplicated", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            duplicated = duplicate_invoice(created.id, db=db)
            stored_duplicate = db.query(Invoice).filter(Invoice.id == duplicated.id).one()
            posted_lines = db.query(TransactionLine).filter(
                TransactionLine.transaction_id == stored_duplicate.transaction_id
            ).all()

        self.assertIsNotNone(stored_duplicate.transaction_id)
        self.assertEqual(sum(line.debit for line in posted_lines), Decimal("115.00"))
        self.assertEqual(sum(line.credit for line in posted_lines), Decimal("115.00"))

    def test_estimate_conversion_posts_converted_invoice_journal_entry(self):
        from app.routes.estimates import convert_to_invoice, create_estimate
        from app.schemas.estimates import EstimateCreate, EstimateLineCreate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            estimate = create_estimate(EstimateCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[EstimateLineCreate(description="Convert", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            converted = convert_to_invoice(estimate.id, db=db)
            stored_invoice = db.query(Invoice).filter(Invoice.id == converted.id).one()
            posted_lines = db.query(TransactionLine).filter(
                TransactionLine.transaction_id == stored_invoice.transaction_id
            ).all()

        self.assertIsNotNone(stored_invoice.transaction_id)
        self.assertEqual(sum(line.debit for line in posted_lines), Decimal("115.00"))
        self.assertEqual(sum(line.credit for line in posted_lines), Decimal("115.00"))

    def test_po_conversion_posts_converted_bill_journal_entry(self):
        from app.routes.purchase_orders import convert_to_bill, create_po
        from app.schemas.purchase_orders import POCreate, POLineCreate

        with self.Session() as db:
            _customer, vendor = self._seed_parties_and_accounts(db)
            po = create_po(POCreate(
                vendor_id=vendor.id,
                date=date(2026, 4, 13),
                lines=[POLineCreate(description="Convert", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            result = convert_to_bill(po.id, db=db)
            stored_bill = db.query(Bill).filter(Bill.id == result["bill_id"]).one()
            posted_lines = db.query(TransactionLine).filter(
                TransactionLine.transaction_id == stored_bill.transaction_id
            ).all()

        self.assertIsNotNone(stored_bill.transaction_id)
        self.assertEqual(sum(line.debit for line in posted_lines), Decimal("115.00"))
        self.assertEqual(sum(line.credit for line in posted_lines), Decimal("115.00"))

    def test_posted_bill_line_update_reverses_old_journal_and_posts_replacement(self):
        from app.routes.bills import create_bill, update_bill
        from app.schemas.bills import BillCreate, BillLineCreate, BillUpdate

        with self.Session() as db:
            _customer, vendor = self._seed_parties_and_accounts(db)
            created = create_bill(BillCreate(
                vendor_id=vendor.id,
                bill_number="B-200",
                date=date(2026, 4, 13),
                lines=[BillLineCreate(description="Original bill", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            original_transaction_id = db.query(Bill).filter(Bill.id == created.id).one().transaction_id

            updated = update_bill(created.id, BillUpdate(
                lines=[BillLineCreate(description="Replacement bill", quantity=1, rate=Decimal("200"), gst_code="GST15")],
            ), db=db)
            stored_bill = db.query(Bill).filter(Bill.id == created.id).one()
            expense_account = db.query(Account).filter(Account.account_number == "6000").one()
            gst_account = db.query(Account).filter(Account.account_number == "2200").one()
            ap_account = db.query(Account).filter(Account.account_number == "2000").one()
            transactions = db.query(Transaction).filter(Transaction.source_id == created.id).order_by(Transaction.id).all()

        self.assertEqual(updated.subtotal, Decimal("200.00"))
        self.assertEqual(updated.tax_amount, Decimal("30.00"))
        self.assertEqual(updated.total, Decimal("230.00"))
        self.assertNotEqual(stored_bill.transaction_id, original_transaction_id)
        self.assertEqual([txn.source_type for txn in transactions], ["bill", "bill_reversal", "bill"])
        self.assertEqual(expense_account.balance, Decimal("200.00"))
        self.assertEqual(gst_account.balance, Decimal("-30.00"))
        self.assertEqual(ap_account.balance, Decimal("230.00"))

    def test_posted_bill_metadata_update_does_not_repost_journal(self):
        from app.routes.bills import create_bill, update_bill
        from app.schemas.bills import BillCreate, BillLineCreate, BillUpdate

        with self.Session() as db:
            _customer, vendor = self._seed_parties_and_accounts(db)
            created = create_bill(BillCreate(
                vendor_id=vendor.id,
                bill_number="B-201",
                date=date(2026, 4, 13),
                lines=[BillLineCreate(description="Original bill", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            original_transaction_id = db.query(Bill).filter(Bill.id == created.id).one().transaction_id

            updated = update_bill(created.id, BillUpdate(notes="Updated note", due_date=date(2026, 5, 13)), db=db)
            stored_bill = db.query(Bill).filter(Bill.id == created.id).one()
            transactions = db.query(Transaction).filter(Transaction.source_id == created.id).order_by(Transaction.id).all()

        self.assertEqual(updated.notes, "Updated note")
        self.assertEqual(str(updated.due_date), "2026-05-13")
        self.assertEqual(stored_bill.transaction_id, original_transaction_id)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].source_type, "bill")

    def test_paid_bill_financial_edit_is_rejected(self):
        from fastapi import HTTPException
        from app.routes.bills import create_bill, update_bill
        from app.routes.bill_payments import create_bill_payment
        from app.schemas.bills import BillCreate, BillLineCreate, BillPaymentAllocationCreate, BillPaymentCreate, BillUpdate

        with self.Session() as db:
            _customer, vendor = self._seed_parties_and_accounts(db)
            db.add(Account(name="Business Bank Account", account_number="1000", account_type=AccountType.ASSET))
            db.commit()
            created = create_bill(BillCreate(
                vendor_id=vendor.id,
                bill_number="B-202",
                date=date(2026, 4, 13),
                lines=[BillLineCreate(description="Original bill", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            create_bill_payment(BillPaymentCreate(
                vendor_id=vendor.id,
                date=date(2026, 4, 14),
                amount=115,
                allocations=[BillPaymentAllocationCreate(bill_id=created.id, amount=115)],
            ), db=db)

            with self.assertRaises(HTTPException) as ctx:
                update_bill(created.id, BillUpdate(
                    lines=[BillLineCreate(description="Replacement bill", quantity=1, rate=Decimal("200"), gst_code="GST15")],
                ), db=db)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("payments", ctx.exception.detail.lower())

    def test_credit_memo_line_update_reverses_old_journal_and_posts_replacement(self):
        from app.routes.credit_memos import create_credit_memo, update_credit_memo
        from app.schemas.credit_memos import CreditMemoCreate, CreditMemoLineCreate, CreditMemoUpdate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            created = create_credit_memo(CreditMemoCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[CreditMemoLineCreate(description="Original credit", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            original_transaction_id = db.query(CreditMemo).filter(CreditMemo.id == created.id).one().transaction_id

            updated = update_credit_memo(created.id, CreditMemoUpdate(
                lines=[CreditMemoLineCreate(description="Replacement credit", quantity=1, rate=Decimal("200"), gst_code="GST15")],
            ), db=db)
            stored_credit = db.query(CreditMemo).filter(CreditMemo.id == created.id).one()
            ar_account = db.query(Account).filter(Account.account_number == "1100").one()
            gst_account = db.query(Account).filter(Account.account_number == "2200").one()
            income_account = db.query(Account).filter(Account.account_number == "4000").one()
            transactions = db.query(Transaction).filter(Transaction.source_id == created.id).order_by(Transaction.id).all()

        self.assertEqual(updated.subtotal, Decimal("200.00"))
        self.assertEqual(updated.tax_amount, Decimal("30.00"))
        self.assertEqual(updated.total, Decimal("230.00"))
        self.assertNotEqual(stored_credit.transaction_id, original_transaction_id)
        self.assertEqual([txn.source_type for txn in transactions], ["credit_memo", "credit_memo_reversal", "credit_memo"])
        self.assertEqual(ar_account.balance, Decimal("-230.00"))
        self.assertEqual(gst_account.balance, Decimal("-30.00"))
        self.assertEqual(income_account.balance, Decimal("-200.00"))

    def test_applied_credit_memo_financial_edit_is_rejected(self):
        from fastapi import HTTPException
        from app.routes.credit_memos import create_credit_memo, update_credit_memo, apply_credit
        from app.routes.invoices import create_invoice
        from app.schemas.credit_memos import CreditApplicationCreate, CreditMemoCreate, CreditMemoLineCreate, CreditMemoUpdate
        from app.schemas.invoices import InvoiceCreate, InvoiceLineCreate

        with self.Session() as db:
            customer, _vendor = self._seed_parties_and_accounts(db)
            invoice = create_invoice(InvoiceCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[InvoiceLineCreate(description="Invoice", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            created = create_credit_memo(CreditMemoCreate(
                customer_id=customer.id,
                date=date(2026, 4, 13),
                lines=[CreditMemoLineCreate(description="Original credit", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            apply_credit(created.id, CreditApplicationCreate(invoice_id=invoice.id, amount=50), db=db)

            with self.assertRaises(HTTPException) as ctx:
                update_credit_memo(created.id, CreditMemoUpdate(
                    lines=[CreditMemoLineCreate(description="Replacement credit", quantity=1, rate=Decimal("200"), gst_code="GST15")],
                ), db=db)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("applications", ctx.exception.detail.lower())

    def test_closing_date_blocks_bill_financial_repost(self):
        from fastapi import HTTPException
        from app.routes.bills import create_bill, update_bill
        from app.schemas.bills import BillCreate, BillLineCreate, BillUpdate

        with self.Session() as db:
            _customer, vendor = self._seed_parties_and_accounts(db)
            created = create_bill(BillCreate(
                vendor_id=vendor.id,
                bill_number="B-203",
                date=date(2026, 4, 13),
                lines=[BillLineCreate(description="Original bill", quantity=1, rate=Decimal("100"), gst_code="GST15")],
            ), db=db)
            db.add(Settings(key="closing_date", value="2026-04-13"))
            db.commit()

            with self.assertRaises(HTTPException) as ctx:
                update_bill(created.id, BillUpdate(
                    lines=[BillLineCreate(description="Replacement bill", quantity=1, rate=Decimal("200"), gst_code="GST15")],
                ), db=db)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("closing date", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()

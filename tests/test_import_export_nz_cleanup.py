import csv
import io
import os
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base
from app.models.accounts import Account, AccountType
from app.models.contacts import Customer, Vendor
from app.models.invoices import Invoice, InvoiceStatus


class ImportExportNzCleanupTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _seed_core(self, db):
        customer = Customer(name="Aroha Ltd", bill_address1="1 Queen Street", bill_city="Auckland", bill_state="Auckland", bill_zip="1010")
        vendor = Vendor(name="Harbour Supplies", address1="2 Willis Street", city="Wellington", state="Wellington", zip="6011")
        db.add_all([
            customer,
            vendor,
            Account(name="Accounts Receivable", account_number="1100", account_type=AccountType.ASSET),
            Account(name="Accounts Payable", account_number="2000", account_type=AccountType.LIABILITY),
            Account(name="GST", account_number="2200", account_type=AccountType.LIABILITY),
            Account(name="Sales", account_number="4000", account_type=AccountType.INCOME),
            Account(name="Purchases", account_number="6000", account_type=AccountType.EXPENSE),
        ])
        db.commit()
        return customer, vendor

    def test_invoice_csv_export_uses_gst_header(self):
        from app.services.csv_export import export_invoices

        with self.Session() as db:
            customer, _vendor = self._seed_core(db)
            db.add(Invoice(
                invoice_number="1001",
                customer_id=customer.id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 1),
                subtotal=Decimal("100.00"),
                tax_amount=Decimal("15.00"),
                total=Decimal("115.00"),
                amount_paid=Decimal("0.00"),
                balance_due=Decimal("115.00"),
            ))
            db.commit()
            header = next(csv.reader(io.StringIO(export_invoices(db))))

        self.assertIn("GST", header)
        self.assertNotIn("Tax", header)

    def test_iif_export_uses_gst_account_and_memo_labels(self):
        from app.services.iif_export import export_estimates, export_invoices
        from app.models.estimates import Estimate, EstimateLine, EstimateStatus
        from app.models.invoices import InvoiceLine

        with self.Session() as db:
            customer, _vendor = self._seed_core(db)
            invoice = Invoice(
                invoice_number="1001",
                customer_id=customer.id,
                status=InvoiceStatus.SENT,
                date=date(2026, 4, 1),
                subtotal=Decimal("100.00"),
                tax_amount=Decimal("15.00"),
                total=Decimal("115.00"),
                amount_paid=Decimal("0.00"),
                balance_due=Decimal("115.00"),
            )
            db.add(invoice)
            db.flush()
            db.add(InvoiceLine(invoice_id=invoice.id, description="Consulting", quantity=1, rate=Decimal("100.00"), amount=Decimal("100.00")))
            estimate = Estimate(
                estimate_number="E-1001",
                customer_id=customer.id,
                status=EstimateStatus.PENDING,
                date=date(2026, 4, 2),
                subtotal=Decimal("100.00"),
                tax_amount=Decimal("15.00"),
                total=Decimal("115.00"),
            )
            db.add(estimate)
            db.flush()
            db.add(EstimateLine(estimate_id=estimate.id, description="Estimate work", quantity=1, rate=Decimal("100.00"), amount=Decimal("100.00")))
            db.commit()

            invoice_iif = export_invoices(db)
            estimate_iif = export_estimates(db)

        self.assertIn("\tGST\t", invoice_iif)
        self.assertIn("\tGST\r\n", invoice_iif)
        self.assertNotIn("Sales Tax Payable", invoice_iif)
        self.assertNotIn("Sales Tax", invoice_iif)
        self.assertIn("\tGST\t", estimate_iif)
        self.assertNotIn("Sales Tax Payable", estimate_iif)

    def test_iif_import_accepts_legacy_and_nz_gst_account_names(self):
        from app.services.iif_import import import_all

        legacy_iif = """!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\n!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tQNTY\tPRICE\tMEMO\n!ENDTRNS\nTRNS\tINVOICE\t04/01/2026\tAccounts Receivable\tAroha Ltd\t115.00\t1001\t\nSPL\tINVOICE\t04/01/2026\tSales\tAroha Ltd\t-100.00\t1001\t1\t100.00\tConsulting\nSPL\tINVOICE\t04/01/2026\tSales Tax Payable\tAroha Ltd\t-15.00\t1001\t\t\tGST\nENDTRNS\n"""
        nz_iif = legacy_iif.replace("Sales Tax Payable", "GST")

        with self.Session() as db:
            self._seed_core(db)
            legacy_result = import_all(db, legacy_iif)
            nz_result = import_all(db, nz_iif.replace("1001", "1002"))

        self.assertEqual(legacy_result["invoices"], 1)
        self.assertEqual(nz_result["invoices"], 1)
        self.assertEqual(legacy_result["errors"], [])
        self.assertEqual(nz_result["errors"], [])


if __name__ == "__main__":
    unittest.main()

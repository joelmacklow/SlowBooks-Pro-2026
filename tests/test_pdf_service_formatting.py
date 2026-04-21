import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.services import pdf_service


class CapturingHTML:
    rendered = []

    def __init__(self, string, **_kwargs):
        self.string = string
        self.__class__.rendered.append(string)

    def write_pdf(self):
        return self.string.encode()


class PdfServiceFormattingTests(unittest.TestCase):
    def setUp(self):
        CapturingHTML.rendered = []
        pdf_service.HTML = CapturingHTML
        self.company = {
            "locale": "en-NZ",
            "currency": "NZD",
            "company_name": "SlowBooks NZ",
            "company_logo_path": "/static/uploads/company_logo.png",
            "gst_number": "123-456-789",
        }

    def test_invoice_pdf_uses_rendered_company_settings(self):
        invoice = SimpleNamespace(
            invoice_number="1001",
            date=date(2026, 4, 13),
            due_date=date(2026, 4, 20),
            terms="Net 7",
            po_number=None,
            customer_name="",
            customer=SimpleNamespace(
                name="Aroha Ltd",
                company="Aroha Holdings",
                email="aroha@example.com",
                phone="021 123 4567",
            ),
            bill_address1="10 Lambton Quay",
            bill_address2="",
            bill_city="Wellington",
            bill_state="Wellington",
            bill_zip="6011",
            ship_address1="",
            lines=[SimpleNamespace(description="Consulting", quantity=1, rate=Decimal("1234.5"), amount=Decimal("1234.5"))],
            subtotal=Decimal("1234.5"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total=Decimal("1234.5"),
            amount_paid=Decimal("0"),
            balance_due=Decimal("1234.5"),
            notes=None,
        )

        fake_logo = Path("/tmp/slowbooks-test-logo.png")
        with mock.patch("app.services.pdf_service.Path.exists", autospec=True) as mock_exists, \
             mock.patch("app.services.pdf_service.UPLOADS_DIR", Path("/tmp")):
            mock_exists.side_effect = lambda path_obj: str(path_obj) == str(fake_logo)
            company = dict(self.company)
            company["company_logo_path"] = "/static/uploads/slowbooks-test-logo.png"
            pdf_service.generate_invoice_pdf(invoice, company)

        rendered = CapturingHTML.rendered[-1]
        self.assertIn("@page { size: A4; margin: 1.5cm; }", rendered)
        self.assertIn('class="company-logo"', rendered)
        self.assertIn(fake_logo.as_uri(), rendered)
        self.assertNotIn('<div class="company-name">SlowBooks NZ</div>', rendered)
        self.assertIn('GST Number', rendered)
        self.assertIn('123-456-789', rendered)
        self.assertIn("13 Apr 2026", rendered)
        self.assertIn("20 Apr 2026", rendered)
        self.assertNotIn("Due 20 Apr 2026", rendered)
        self.assertIn("$1,234.50", rendered)
        self.assertIn("Payment Advice", rendered)
        self.assertIn("Aroha Ltd", rendered)
        self.assertIn("Aroha Holdings", rendered)
        self.assertIn("aroha@example.com", rendered)
        self.assertIn("021 123 4567", rendered)
        self.assertIn("Wellington Wellington 6011", rendered)
        self.assertIn('class="no-wrap"', rendered)
        self.assertIn('payment-advice-table', rendered)

    def test_estimate_pdf_uses_rendered_company_settings(self):
        estimate = SimpleNamespace(
            estimate_number="E-1001",
            date=date(2026, 4, 13),
            expiration_date=date(2026, 5, 13),
            status=SimpleNamespace(value="draft"),
            customer=SimpleNamespace(name="Aroha Ltd"),
            bill_address1="",
            bill_address2="",
            bill_city="",
            bill_state="",
            bill_zip="",
            lines=[SimpleNamespace(description="Consulting", quantity=1, rate=Decimal("1234.5"), amount=Decimal("1234.5"))],
            subtotal=Decimal("1234.5"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total=Decimal("1234.5"),
            notes=None,
        )

        pdf_service.generate_estimate_pdf(estimate, self.company)

        rendered = CapturingHTML.rendered[-1]
        self.assertIn("@page { size: A4; margin: 1.5cm; }", rendered)
        self.assertIn("13 Apr 2026", rendered)
        self.assertIn("13 May 2026", rendered)
        self.assertIn("$1,234.50", rendered)
        self.assertIn("ESTIMATE", rendered)
        self.assertIn("Quote Summary", rendered)

    def test_statement_pdf_uses_rendered_company_settings(self):
        customer = SimpleNamespace(
            name="Aroha Ltd",
            bill_address1="",
            bill_address2="",
            bill_city="",
            bill_state="",
            bill_zip="",
        )
        invoices = [
            SimpleNamespace(
                date=date(2026, 4, 13),
                invoice_number="1001",
                notes="",
                total=Decimal("1234.5"),
            )
        ]
        payments = [
            SimpleNamespace(
                date=date(2026, 4, 20),
                reference="PMT-1",
                check_number="",
                method="Bank",
                amount=Decimal("234.5"),
            )
        ]

        pdf_service.generate_statement_pdf(
            customer, invoices, payments, self.company, as_of_date=date(2026, 4, 30)
        )

        rendered = CapturingHTML.rendered[-1]
        self.assertIn("@page { size: A4; margin: 1.5cm; }", rendered)
        self.assertIn("30 Apr 2026", rendered)
        self.assertIn("13 Apr 2026", rendered)
        self.assertIn("20 Apr 2026", rendered)
        self.assertIn("$1,234.50", rendered)
        self.assertIn("$234.50", rendered)
        self.assertIn("$1,000.00", rendered)
        self.assertIn("Balance Summary", rendered)
        self.assertIn("Payment Advice", rendered)

    def test_payroll_payslip_pdf_uses_nz_payroll_labels_and_company_settings(self):
        pay_run = SimpleNamespace(
            id=7,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 14),
            pay_date=date(2026, 4, 15),
            tax_year=2027,
        )
        employee = SimpleNamespace(
            first_name="Aroha",
            last_name="Ngata",
        )
        stub = SimpleNamespace(
            tax_code="M",
            hours=Decimal("0"),
            gross_pay=Decimal("3000.00"),
            paye=Decimal("600.78"),
            acc_earners_levy=Decimal("52.50"),
            student_loan_deduction=Decimal("0.00"),
            kiwisaver_employee_deduction=Decimal("105.00"),
            employer_kiwisaver_contribution=Decimal("105.00"),
            esct=Decimal("18.37"),
            child_support_deduction=Decimal("0.00"),
            net_pay=Decimal("2241.72"),
        )

        pdf_service.generate_payroll_payslip_pdf(pay_run, stub, employee, self.company)

        rendered = CapturingHTML.rendered[-1]
        self.assertIn("@page { size: A4; margin: 1.5cm; }", rendered)
        self.assertIn("Payslip", rendered)
        self.assertIn("Aroha Ngata", rendered)
        self.assertIn("15 Apr 2026", rendered)
        self.assertIn("PAYE", rendered)
        self.assertIn("ACC Earners' Levy", rendered)
        self.assertIn("$2,241.72", rendered)

    def test_credit_memo_pdf_uses_rendered_company_settings(self):
        credit_memo = SimpleNamespace(
            memo_number="CM-0001",
            date=date(2026, 4, 13),
            customer=SimpleNamespace(name="Aroha Ltd"),
            lines=[SimpleNamespace(description="Refund", quantity=1, rate=Decimal("1234.5"), amount=Decimal("1234.5"))],
            subtotal=Decimal("1234.5"),
            tax_amount=Decimal("185.18"),
            total=Decimal("1419.68"),
            notes=None,
        )

        pdf_service.generate_credit_memo_pdf(credit_memo, self.company)

        rendered = CapturingHTML.rendered[-1]
        self.assertIn("@page { size: A4; margin: 1.5cm; }", rendered)
        self.assertIn("CREDIT NOTE", rendered)
        self.assertIn("13 Apr 2026", rendered)
        self.assertIn("$1,419.68", rendered)
        self.assertIn("Credit Summary", rendered)

    def test_purchase_order_pdf_uses_rendered_company_settings(self):
        purchase_order = SimpleNamespace(
            po_number="PO-0001",
            date=date(2026, 4, 13),
            expected_date=date(2026, 4, 20),
            vendor=SimpleNamespace(name="Harbour Supplies"),
            ship_to="SlowBooks NZ",
            lines=[SimpleNamespace(description="Stationery", quantity=1, rate=Decimal("1234.5"), amount=Decimal("1234.5"))],
            subtotal=Decimal("1234.5"),
            tax_amount=Decimal("185.18"),
            total=Decimal("1419.68"),
            notes=None,
        )

        pdf_service.generate_purchase_order_pdf(purchase_order, self.company)

        rendered = CapturingHTML.rendered[-1]
        self.assertIn("@page { size: A4; margin: 1.5cm; }", rendered)
        self.assertIn("Purchase Order", rendered)
        self.assertIn("20 Apr 2026", rendered)
        self.assertIn("$1,419.68", rendered)
        self.assertIn("Delivery Details", rendered)

    def test_invoice_pdf_escapes_untrusted_html_fields(self):
        invoice = SimpleNamespace(
            invoice_number="1001",
            date=date(2026, 4, 13),
            due_date=date(2026, 4, 20),
            terms="<b>Net 7</b>",
            po_number=None,
            customer_name="<script>alert(1)</script>",
            bill_address1="",
            bill_address2="",
            bill_city="",
            bill_state="",
            bill_zip="",
            ship_address1="",
            lines=[SimpleNamespace(description="<img src=x onerror=alert(1)>", quantity=1, rate=Decimal("1234.5"), amount=Decimal("1234.5"))],
            subtotal=Decimal("1234.5"),
            tax_rate=Decimal("0"),
            tax_amount=Decimal("0"),
            total=Decimal("1234.5"),
            amount_paid=Decimal("0"),
            balance_due=Decimal("1234.5"),
            notes="<svg onload=alert(1)>",
        )

        pdf_service.generate_invoice_pdf(invoice, self.company)

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", CapturingHTML.rendered[-1])
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", CapturingHTML.rendered[-1])
        self.assertIn("&lt;svg onload=alert(1)&gt;", CapturingHTML.rendered[-1])
        self.assertIn("&lt;b&gt;Net 7&lt;/b&gt;", CapturingHTML.rendered[-1])
        self.assertNotIn("<script>alert(1)</script>", CapturingHTML.rendered[-1])
        self.assertNotIn("<img src=x onerror=alert(1)>", CapturingHTML.rendered[-1])
        self.assertNotIn("<svg onload=alert(1)>", CapturingHTML.rendered[-1])
        self.assertNotIn("<b>Net 7</b>", CapturingHTML.rendered[-1])

    def test_report_pdf_uses_a4_page_size_with_1_5cm_margins(self):
        pdf_service.generate_report_pdf(
            title="Trial Balance",
            company_settings=self.company,
            subtitle="As of 30 Apr 2026",
            tables=[{
                "columns": [{"label": "Account"}, {"label": "Debit", "align": "right"}],
                "rows": [{
                    "cells": [{"text": "Business Bank"}, {"text": "$92.00", "align": "right"}],
                }],
            }],
            landscape=False,
        )

        rendered = CapturingHTML.rendered[-1]
        self.assertIn("@page { size: A4; margin: 1.5cm; }", rendered)
        self.assertIn("position: fixed; bottom: 0;", rendered)
        self.assertIn("Trial Balance", rendered)


if __name__ == "__main__":
    unittest.main()

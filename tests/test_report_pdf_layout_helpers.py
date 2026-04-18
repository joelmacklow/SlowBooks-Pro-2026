import os
import sys
import types
import unittest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)


class ReportPdfLayoutHelperTests(unittest.TestCase):
    def test_income_by_customer_tables_use_narrowed_pdf_width(self):
        from app.routes import reports as reports_route

        report = {
            "items": [
                {
                    "customer_name": "Aroha Ltd",
                    "invoice_count": 2,
                    "total_sales": 1200.0,
                    "total_paid": 800.0,
                    "total_balance": 400.0,
                }
            ],
            "total_sales": 1200.0,
            "total_paid": 800.0,
            "total_balance": 400.0,
        }

        tables = reports_route._report_tables_income_by_customer(report, {"locale": "en-NZ", "currency": "NZD"})
        self.assertEqual(tables[0]["style"], "width: 92%;")

    def test_general_ledger_tables_use_narrowed_pdf_width(self):
        from app.routes import reports as reports_route

        report = {
            "accounts": [
                {
                    "account_number": "090",
                    "account_name": "Business Bank",
                    "entries": [
                        {
                            "date": "2026-04-01",
                            "description": "Receipt",
                            "reference": "INV-1001",
                            "debit": 115.0,
                            "credit": 0.0,
                        }
                    ],
                    "total_debit": 115.0,
                    "total_credit": 0.0,
                }
            ]
        }

        tables = reports_route._report_tables_general_ledger(report, {"locale": "en-NZ", "currency": "NZD"})
        self.assertEqual(tables[0]["style"], "width: 92%;")


if __name__ == "__main__":
    unittest.main()

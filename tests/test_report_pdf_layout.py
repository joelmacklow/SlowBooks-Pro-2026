import os
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

class ReportPdfLayoutTests(unittest.TestCase):
    def test_shared_report_template_prevents_amount_wrapping_and_centers_tables(self):
        template = Path("app/templates/report_pdf.html").read_text()
        self.assertIn("margin: 0 auto 14px auto;", template)
        self.assertIn("white-space: nowrap;", template)
        self.assertIn("@bottom-left { content: element(report-footer); }", template)
        self.assertIn("@bottom-right { content: \"Page \" counter(page) \" of \" counter(pages); }", template)
        self.assertNotIn("position: fixed; bottom: 0;", template)

    def test_header_logo_copy_is_larger_and_report_tile_is_slightly_narrower(self):
        shared_theme = Path("app/templates/_document_theme.html").read_text()
        report_template = Path("app/templates/report_pdf.html").read_text()

        self.assertIn("max-width: 3.2cm;", shared_theme)
        self.assertIn("max-height: 1.8cm;", shared_theme)
        self.assertIn("min-width: 4.4cm;", shared_theme)
        self.assertIn("max-width: 54%;", report_template)
        self.assertIn("max-width: 3.4cm;", report_template)
        self.assertIn("max-height: 2cm;", report_template)

    def test_fixed_asset_reconciliation_pdf_uses_compact_table_style(self):
        from app.routes.reports import fixed_assets_reconciliation_pdf

        captured = {}
        report_payload = {
            "as_of_date": "2026-04-30",
            "assets": [
                {
                    "asset_number": "FA-0001",
                    "asset_name": "Laptop Fleet",
                    "asset_type": "Computer Equipment",
                    "purchase_date": "2026-04-01",
                    "purchase_price": 999999.99,
                    "accumulated_depreciation": 123456.78,
                    "book_value": 876543.21,
                }
            ],
            "total_cost": 999999.99,
            "total_accumulated_depreciation": 123456.78,
            "total_book_value": 876543.21,
        }
        with mock.patch("app.routes.reports.fixed_assets_reconciliation_report", return_value=report_payload), \
             mock.patch("app.routes.reports.generate_report_pdf", side_effect=lambda **kwargs: captured.update(kwargs) or b"%PDF-fixed-assets"), \
             mock.patch("app.routes.reports._company_settings", return_value={"company_name": "SlowBooks NZ", "currency": "NZD", "locale": "en-NZ"}):
            response = fixed_assets_reconciliation_pdf(as_of_date=date(2026, 4, 30), db=mock.Mock(), auth={"user_id": 1})

        self.assertEqual(response.media_type, "application/pdf")
        self.assertEqual(captured["title"], "Fixed Asset Reconciliation")
        self.assertIn("width: 88%;", captured["tables"][0]["style"])
        self.assertIn("font-size: 8pt;", captured["tables"][0]["style"])
        self.assertEqual(captured["tables"][0]["columns"][-3:], [
            {"label": "Cost", "align": "right", "width": "10%"},
            {"label": "Accum. Dep.", "align": "right", "width": "11%"},
            {"label": "Book Value", "align": "right", "width": "11%"},
        ])
        self.assertEqual(captured["subtitle"], "As of 30 Apr 2026")


if __name__ == "__main__":
    unittest.main()

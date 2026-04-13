import os
import unittest
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base


class NzChartSeedTests(unittest.TestCase):
    def setUp(self):
        from app.models.accounts import Account  # noqa: F401
        from app.models.settings import Settings  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_chart_seed_matches_nz_default_accounts(self):
        from app.seed.chart_of_accounts import CHART_OF_ACCOUNTS

        account_numbers = {row["account_number"]: row for row in CHART_OF_ACCOUNTS}

        self.assertEqual(account_numbers["090"]["name"], "Business Bank Account")
        self.assertEqual(account_numbers["091"]["name"], "Business Savings Account")
        self.assertEqual(account_numbers["200"]["name"], "Sales")
        self.assertEqual(account_numbers["300"]["name"], "Purchases")
        self.assertEqual(account_numbers["610"]["name"], "Accounts Receivable")
        self.assertEqual(account_numbers["800"]["name"], "Accounts Payable")
        self.assertEqual(account_numbers["820"]["name"], "GST")
        self.assertEqual(account_numbers["825"]["name"], "PAYE Payable")
        self.assertEqual(account_numbers["477"]["name"], "Salaries")
        self.assertEqual(account_numbers["478"]["name"], "KiwiSaver Employer Contributions")
        self.assertNotIn("1000", account_numbers)
        self.assertNotIn("1100", account_numbers)
        self.assertNotIn("2000", account_numbers)
        self.assertNotIn("4000", account_numbers)
        self.assertNotIn("6000", account_numbers)

    def test_seed_database_populates_system_account_role_settings(self):
        from app.models.settings import Settings
        import scripts.seed_database as seed_database

        seed_database.SessionLocal = self.Session
        seed_database.seed()

        with self.Session() as db:
            settings = {row.key: row.value for row in db.query(Settings).all()}

        self.assertEqual(settings["system_account_default_bank_id"], "1")
        self.assertTrue(settings["system_account_accounts_receivable_id"])
        self.assertTrue(settings["system_account_accounts_payable_id"])
        self.assertTrue(settings["system_account_gst_control_id"])
        self.assertTrue(settings["system_account_default_sales_income_id"])
        self.assertTrue(settings["system_account_default_expense_id"])
        self.assertTrue(settings["system_account_wages_expense_id"])
        self.assertTrue(settings["system_account_employer_kiwisaver_expense_id"])
        self.assertTrue(settings["system_account_paye_payable_id"])
        self.assertTrue(settings["system_account_payroll_clearing_id"])


if __name__ == "__main__":
    unittest.main()

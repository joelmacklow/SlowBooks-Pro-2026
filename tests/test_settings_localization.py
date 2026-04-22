import unittest
import os
import sys
import types
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base
from app.routes.settings import _get_all, get_public_settings, update_settings


class SettingsLocalizationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_settings_include_nz_localization_defaults(self):
        with self.Session() as db:
            settings = _get_all(db)

        self.assertEqual(settings["country"], "NZ")
        self.assertEqual(settings["tax_regime"], "NZ")
        self.assertEqual(settings["currency"], "NZD")
        self.assertEqual(settings["locale"], "en-NZ")
        self.assertEqual(settings["timezone"], "Pacific/Auckland")
        self.assertEqual(settings["ird_number"], "")
        self.assertEqual(settings["gst_number"], "")
        self.assertEqual(settings["gst_registered"], "false")
        self.assertEqual(settings["gst_basis"], "invoice")
        self.assertEqual(settings["gst_period"], "two-monthly")
        self.assertEqual(settings["prices_include_gst"], "false")

    def test_settings_update_persists_nz_localization_keys(self):
        data = {
            "country": "NZ",
            "tax_regime": "NZ",
            "currency": "NZD",
            "locale": "en-NZ",
            "timezone": "Pacific/Auckland",
            "ird_number": "123-456-789",
            "gst_number": "123-456-789",
            "gst_registered": "true",
            "gst_basis": "payments",
            "gst_period": "six-monthly",
            "prices_include_gst": "true",
        }

        with self.Session() as db:
            with mock.patch("app.routes.settings.lock_context_for_client", return_value={}):
                settings = update_settings(data, db)

        for key, value in data.items():
            self.assertEqual(settings[key], value)

    def test_public_settings_expose_financial_year_start(self):
        with self.Session() as db:
            with mock.patch("app.routes.settings.lock_context_for_client", return_value={}):
                update_settings({"financial_year_start": "04-01", "financial_year_end": "03-31"}, db)
            public_settings = get_public_settings(db)

        self.assertEqual(public_settings["financial_year_start"], "04-01")


if __name__ == "__main__":
    unittest.main()

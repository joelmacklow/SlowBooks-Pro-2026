import unittest
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base
from app.routes.settings import _get_all, update_settings


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
            settings = update_settings(data, db)

        for key, value in data.items():
            self.assertEqual(settings[key], value)


if __name__ == "__main__":
    unittest.main()

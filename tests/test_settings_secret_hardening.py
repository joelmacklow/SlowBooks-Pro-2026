import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base
from app.models.settings import Settings
from app.routes.settings import get_settings, update_settings


class SettingsSecretHardeningTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_update_settings_hashes_closing_date_password_and_masks_response(self):
        with self.Session() as db:
            settings = update_settings(
                {"closing_date_password": "letmein"},
                db=db,
            )
            stored = db.query(Settings).filter(Settings.key == "closing_date_password").one().value

        self.assertTrue(stored.startswith("pbkdf2_sha256$"))
        self.assertEqual(settings["closing_date_password"], "")

    def test_blank_update_preserves_existing_closing_date_password(self):
        with self.Session() as db:
            update_settings({"closing_date_password": "letmein"}, db=db)
            original = db.query(Settings).filter(Settings.key == "closing_date_password").one().value

            settings = update_settings(
                {"company_name": "Updated Co", "closing_date_password": ""},
                db=db,
            )
            stored = db.query(Settings).filter(Settings.key == "closing_date_password").one().value

        self.assertEqual(stored, original)
        self.assertEqual(settings["closing_date_password"], "")
        self.assertEqual(settings["company_name"], "Updated Co")

    def test_get_settings_masks_existing_closing_date_password(self):
        with self.Session() as db:
            update_settings({"closing_date_password": "letmein"}, db=db)
            settings = get_settings(db=db, auth={"user_id": 1})

        self.assertEqual(settings["closing_date_password"], "")

    def test_update_settings_masks_smtp_password_and_preserves_stored_value_on_blank(self):
        with self.Session() as db:
            first = update_settings(
                {"smtp_password": "smtp-secret"},
                db=db,
            )
            original_row = db.query(Settings).filter(Settings.key == "smtp_password").first()
            self.assertIsNone(original_row)

            db.add(Settings(key="smtp_password", value="legacy-secret"))
            db.commit()
            second = update_settings(
                {"company_name": "Updated Co", "smtp_password": ""},
                db=db,
            )
            stored = db.query(Settings).filter(Settings.key == "smtp_password").one().value

        self.assertEqual(first["smtp_password"], "")
        self.assertEqual(second["smtp_password"], "")
        self.assertEqual(second["company_name"], "Updated Co")
        self.assertEqual(stored, "legacy-secret")

    def test_get_settings_masks_existing_smtp_password(self):
        with self.Session() as db:
            update_settings({"smtp_password": "smtp-secret"}, db=db)
            settings = get_settings(db=db, auth={"user_id": 1})

        self.assertEqual(settings["smtp_password"], "")


if __name__ == "__main__":
    unittest.main()

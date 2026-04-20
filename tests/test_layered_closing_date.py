import os
import sys
import types
import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class LayeredClosingDateTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.services import closing_date as closing_date_service

        company_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        master_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=company_engine)
        Base.metadata.create_all(bind=master_engine)
        self.Session = sessionmaker(bind=company_engine)
        self.MasterSession = sessionmaker(bind=master_engine)
        self.closing_date_service = closing_date_service
        self._original_open_master_session = getattr(closing_date_service, "_open_master_session", None)
        self._original_database_name_for_session = getattr(closing_date_service, "_database_name_for_session", None)
        closing_date_service._open_master_session = self.MasterSession
        closing_date_service._database_name_for_session = lambda _db: "bookkeeper"

    def tearDown(self):
        if self._original_open_master_session is not None:
            self.closing_date_service._open_master_session = self._original_open_master_session
        if self._original_database_name_for_session is not None:
            self.closing_date_service._database_name_for_session = self._original_database_name_for_session

    def test_settings_round_trip_includes_financial_year_dates_and_lock_context(self):
        from app.models.companies import Company
        from app.routes.settings import get_settings, update_settings

        with self.MasterSession() as master_db:
            master_db.add(Company(name="Default Company", database_name="bookkeeper", org_lock_date=date(2026, 3, 31)))
            master_db.commit()

        with self.Session() as db:
            update_settings({
                "financial_year_start": "04-01",
                "financial_year_end": "03-31",
                "closing_date": "2026-02-28",
            }, db=db, auth=True)
            settings = get_settings(db=db, auth=True)

        self.assertEqual(settings["financial_year_start"], "04-01")
        self.assertEqual(settings["financial_year_end"], "03-31")
        self.assertEqual(settings["org_lock_date"], "2026-03-31")
        self.assertEqual(settings["effective_lock_date"], "2026-03-31")
        self.assertEqual(settings["effective_lock_layer"], "org_admin")

    def test_company_lock_password_override_still_works_when_org_lock_not_blocking(self):
        from app.models.companies import Company
        from app.models.settings import Settings
        from app.services.closing_date import check_closing_date, hash_closing_date_password, reset_request_closing_date_password, set_request_closing_date_password

        with self.MasterSession() as master_db:
            master_db.add(Company(name="Default Company", database_name="bookkeeper", org_lock_date=date(2026, 1, 31)))
            master_db.commit()

        with self.Session() as db:
            db.add_all([
                Settings(key="closing_date", value="2026-02-28"),
                Settings(key="closing_date_password", value=hash_closing_date_password("secret")),
            ])
            db.commit()

            check_closing_date(db, date(2026, 2, 15), password="secret")
            token = set_request_closing_date_password("secret")
            try:
                check_closing_date(db, date(2026, 2, 15))
            finally:
                reset_request_closing_date_password(token)

    def test_org_lock_cannot_be_bypassed_by_company_password_override(self):
        from app.models.companies import Company
        from app.models.settings import Settings
        from app.services.closing_date import check_closing_date, hash_closing_date_password

        with self.MasterSession() as master_db:
            master_db.add(Company(name="Default Company", database_name="bookkeeper", org_lock_date=date(2026, 3, 31)))
            master_db.commit()

        with self.Session() as db:
            db.add_all([
                Settings(key="closing_date", value="2026-02-28"),
                Settings(key="closing_date_password", value=hash_closing_date_password("secret")),
            ])
            db.commit()

            with self.assertRaises(HTTPException) as ctx:
                check_closing_date(db, date(2026, 3, 15), password="secret")

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("organization lock", ctx.exception.detail.lower())

    def test_financial_year_dates_require_valid_boundaries(self):
        from app.routes.settings import update_settings

        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                update_settings({
                    "financial_year_start": "04-01",
                    "financial_year_end": "02-30",
                }, db=db, auth=True)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("financial year", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from datetime import date
from unittest import mock

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app.database import Base
from app.models.settings import Settings


class ClosingDateSecurityTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_check_closing_date_uses_compare_digest_for_password_override(self):
        from app.services import closing_date

        with self.Session() as db:
            db.add_all([
                Settings(key='closing_date', value='2026-04-30'),
                Settings(key='closing_date_password', value='letmein'),
            ])
            db.commit()

            with mock.patch.object(closing_date.hmac, 'compare_digest', return_value=True) as compare_mock:
                closing_date.check_closing_date(db, date(2026, 4, 30), password='letmein')

        compare_mock.assert_called_once_with('letmein', 'letmein')

    def test_check_closing_date_rejects_wrong_password(self):
        from app.services.closing_date import check_closing_date

        with self.Session() as db:
            db.add_all([
                Settings(key='closing_date', value='2026-04-30'),
                Settings(key='closing_date_password', value='letmein'),
            ])
            db.commit()

            with self.assertRaises(HTTPException) as ctx:
                check_closing_date(db, date(2026, 4, 30), password='wrong')

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn('closing date', ctx.exception.detail.lower())


if __name__ == '__main__':
    unittest.main()

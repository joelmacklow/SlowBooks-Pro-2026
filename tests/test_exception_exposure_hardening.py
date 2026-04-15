import asyncio
import importlib
import os
import sys
import unittest
from io import BytesIO
from unittest import mock

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app.database import Base


class ExceptionExposureHardeningTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _load_csv_routes(self):
        sys.modules.pop('app.routes.csv', None)
        with mock.patch('fastapi.dependencies.utils.ensure_multipart_is_installed', return_value=None):
            return importlib.import_module('app.routes.csv')

    def test_new_company_hides_internal_service_errors(self):
        from app.routes.companies import CompanyCreate, new_company

        with self.Session() as db, mock.patch('app.routes.companies.create_company', return_value={
            'success': False,
            'error': 'psycopg2 failed password=supersecret host=db.internal',
        }):
            with self.assertRaises(HTTPException) as ctx:
                new_company(
                    CompanyCreate(name='Auckland Books', database_name='auckland_books'),
                    db=db,
                    auth={'user_id': 1},
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, 'Failed to create company')

    def test_csv_import_hides_unexpected_import_errors(self):
        csv_routes = self._load_csv_routes()

        upload = UploadFile(filename='customers.csv', file=BytesIO('Name\nAlice\n'.encode('utf-8')))
        with self.Session() as db, mock.patch.object(csv_routes, 'import_customers', side_effect=RuntimeError('dsn=postgres://secret@db/internal')):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(csv_routes.csv_import_customers(file=upload, db=db))

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail, 'CSV import failed')

    def test_csv_import_hides_decode_details(self):
        csv_routes = self._load_csv_routes()

        upload = UploadFile(filename='customers.csv', file=BytesIO(b'\xff\xfe\x00bad'))
        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(csv_routes.csv_import_customers(file=upload, db=db))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, 'CSV file must be UTF-8 encoded')


if __name__ == '__main__':
    unittest.main()

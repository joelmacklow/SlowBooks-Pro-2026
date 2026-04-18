import asyncio
import importlib
import os
import sys
import types
import unittest
from io import BytesIO
from unittest import mock

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class UploadSizeHardeningTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _load_route_module(self, module_name: str):
        sys.modules.pop(module_name, None)
        with mock.patch("fastapi.dependencies.utils.ensure_multipart_is_installed", return_value=None):
            return importlib.import_module(module_name)

    def _oversized_upload(self, filename: str, *, content_type: str = "text/plain", size: int = 2 * 1024 * 1024 + 1):
        return UploadFile(
            filename=filename,
            file=BytesIO(b"x" * size),
            headers=Headers({"content-type": content_type}),
        )

    def test_logo_upload_rejects_oversized_file(self):
        uploads_route = self._load_route_module("app.routes.uploads")

        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    uploads_route.upload_logo(
                        file=self._oversized_upload("logo.png", content_type="image/png"),
                        db=db,
                        auth={"user_id": 1},
                    )
                )

        self.assertEqual(ctx.exception.status_code, 413)
        self.assertIn("too large", ctx.exception.detail.lower())

    def test_csv_import_rejects_oversized_file(self):
        csv_route = self._load_route_module("app.routes.csv")

        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(csv_route.csv_import_customers(file=self._oversized_upload("customers.csv"), db=db, auth={"user_id": 1}))

        self.assertEqual(ctx.exception.status_code, 413)
        self.assertIn("too large", ctx.exception.detail.lower())

    def test_iif_import_rejects_oversized_file(self):
        iif_route = self._load_route_module("app.routes.iif")

        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(iif_route.import_iif(file=self._oversized_upload("data.iif"), db=db, auth={"user_id": 1}))

        self.assertEqual(ctx.exception.status_code, 413)
        self.assertIn("too large", ctx.exception.detail.lower())

    def test_bank_import_rejects_oversized_file(self):
        bank_route = self._load_route_module("app.routes.bank_import")

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(bank_route.preview_statement(file=self._oversized_upload("statement.ofx"), auth={"user_id": 1}))

        self.assertEqual(ctx.exception.status_code, 413)
        self.assertIn("too large", ctx.exception.detail.lower())

    def test_xero_import_rejects_oversized_bundle_member(self):
        xero_route = self._load_route_module("app.routes.xero_import")

        oversized = self._oversized_upload("xero_chart_of_accounts.csv")
        with self.Session() as db:
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(xero_route.dry_run_xero_import(files=[oversized], db=db, auth={"user_id": 1}))

        self.assertEqual(ctx.exception.status_code, 413)
        self.assertIn("too large", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()

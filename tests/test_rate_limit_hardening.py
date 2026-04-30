import asyncio
import os
import sys
import types
import unittest
from io import BytesIO
from pathlib import Path
import importlib
from unittest import mock

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers
from starlette.requests import Request

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def make_request(host: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": [],
        "client": (host, 12345),
        "server": ("testserver", 3001),
        "scheme": "http",
    }
    return Request(scope)


class RateLimitHardeningTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def tearDown(self):
        from app.services.rate_limit import clear_rate_limits

        clear_rate_limits()

    def _load_route_module(self, module_name: str):
        sys.modules.pop(module_name, None)
        with mock.patch("fastapi.dependencies.utils.ensure_multipart_is_installed", return_value=None):
            return importlib.import_module(module_name)

    def test_rate_limit_helper_blocks_after_limit(self):
        from app.services.rate_limit import enforce_rate_limit

        request = make_request("127.0.0.1")
        for _ in range(2):
            enforce_rate_limit(
                request,
                scope="test",
                limit=2,
                window_seconds=60,
                detail="Too many requests",
            )

        with self.assertRaises(HTTPException) as ctx:
            enforce_rate_limit(
                request,
                scope="test",
                limit=2,
                window_seconds=60,
                detail="Too many requests",
            )

        self.assertEqual(ctx.exception.status_code, 429)


    def test_backup_routes_are_rate_limited_when_request_present(self):
        from tempfile import TemporaryDirectory

        backups_route = self._load_route_module("app.routes.backups")
        from app.services import backup_service

        with TemporaryDirectory() as tmpdir, self.Session() as db, \
             mock.patch.object(backup_service, "BACKUP_DIR", Path(tmpdir)), \
             mock.patch.object(backups_route, "create_backup", return_value={"success": True, "filename": "slowbooks_20260418_010101.sql", "file_size": 123}), \
             mock.patch.object(backups_route, "restore_backup", return_value={"success": True, "message": "restored"}):
            backup_file = Path(tmpdir) / "slowbooks_20260418_010101.sql"
            backup_file.write_text("backup-data", encoding="utf-8")

            for _ in range(3):
                create_result = backups_route.make_backup(
                    db=db,
                    auth={"user_id": 1},
                    request=make_request("127.0.0.1"),
                )
                self.assertTrue(create_result["success"])

            with self.assertRaises(HTTPException) as create_ctx:
                backups_route.make_backup(
                    db=db,
                    auth={"user_id": 1},
                    request=make_request("127.0.0.1"),
                )

            for _ in range(10):
                response = backups_route.download_backup(
                    backup_file.name,
                    db=db,
                    auth={"user_id": 1},
                    request=make_request("127.0.0.1"),
                )
                self.assertEqual(response.path, str(backup_file))

            with self.assertRaises(HTTPException) as download_ctx:
                backups_route.download_backup(
                    backup_file.name,
                    db=db,
                    auth={"user_id": 1},
                    request=make_request("127.0.0.1"),
                )

            for _ in range(3):
                restore_result = backups_route.restore(
                    backups_route.RestoreRequest(filename=backup_file.name),
                    db=db,
                    auth={"user_id": 1},
                    request=make_request("127.0.0.2"),
                )
                self.assertTrue(restore_result["success"])

            with self.assertRaises(HTTPException) as restore_ctx:
                backups_route.restore(
                    backups_route.RestoreRequest(filename=backup_file.name),
                    db=db,
                    auth={"user_id": 1},
                    request=make_request("127.0.0.2"),
                )

        self.assertEqual(create_ctx.exception.status_code, 429)
        self.assertEqual(download_ctx.exception.status_code, 429)
        self.assertEqual(restore_ctx.exception.status_code, 429)

    def test_csv_import_is_rate_limited_when_request_present(self):
        csv_route = self._load_route_module("app.routes.csv")

        def make_upload():
            return UploadFile(filename="customers.csv", file=BytesIO("Name\nAlice\n".encode("utf-8")))

        with self.Session() as db:
            for _ in range(10):
                result = asyncio.run(
                    csv_route.csv_import_customers(
                        file=make_upload(),
                        db=db,
                        auth={"user_id": 1},
                        request=make_request("127.0.0.1"),
                    )
                )
                self.assertIn("created", result)

            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    csv_route.csv_import_customers(
                        file=make_upload(),
                        db=db,
                        auth={"user_id": 1},
                        request=make_request("127.0.0.1"),
                    )
                )

        self.assertEqual(ctx.exception.status_code, 429)

    def test_document_email_is_rate_limited_when_request_present(self):
        from app.models.contacts import Customer
        from app.models.invoices import Invoice, InvoiceStatus
        from app.models.settings import Settings
        from datetime import date
        from decimal import Decimal
        from app.routes import invoices as invoices_route
        from app.schemas.email import DocumentEmailRequest

        original_generate = invoices_route.generate_invoice_pdf
        original_render = invoices_route.render_invoice_email
        original_send = invoices_route.send_document_email
        invoices_route.generate_invoice_pdf = lambda *_args, **_kwargs: b"%PDF"
        invoices_route.render_invoice_email = lambda *_args, **_kwargs: "<p>Hello</p>"
        invoices_route.send_document_email = lambda *args, **kwargs: None
        try:
            with self.Session() as db:
                customer = Customer(name="Aroha Ltd", email="customer@example.com")
                invoice = Invoice(
                    invoice_number="1001",
                    customer=customer,
                    status=InvoiceStatus.SENT,
                    date=date(2026, 4, 13),
                    due_date=date(2026, 4, 20),
                    subtotal=Decimal("100.00"),
                    tax_rate=Decimal("0.1500"),
                    tax_amount=Decimal("15.00"),
                    total=Decimal("115.00"),
                    balance_due=Decimal("115.00"),
                )
                db.add_all([
                    customer,
                    invoice,
                    Settings(key="company_name", value="SlowBooks NZ"),
                    Settings(key="locale", value="en-NZ"),
                    Settings(key="currency", value="NZD"),
                ])
                db.commit()

                for _ in range(5):
                    result = invoices_route.email_invoice(
                        invoice.id,
                        DocumentEmailRequest(recipient="customer@example.com"),
                        db=db,
                        auth={"user_id": 1},
                        request=make_request("127.0.0.1"),
                    )
                    self.assertEqual(result["status"], "sent")

                with self.assertRaises(HTTPException) as ctx:
                    invoices_route.email_invoice(
                        invoice.id,
                        DocumentEmailRequest(recipient="customer@example.com"),
                        db=db,
                        auth={"user_id": 1},
                        request=make_request("127.0.0.1"),
                    )
        finally:
            invoices_route.generate_invoice_pdf = original_generate
            invoices_route.render_invoice_email = original_render
            invoices_route.send_document_email = original_send

        self.assertEqual(ctx.exception.status_code, 429)

    def test_direct_route_calls_without_request_still_work(self):
        csv_route = self._load_route_module("app.routes.csv")

        upload = UploadFile(filename="customers.csv", file=BytesIO("Name\nAlice\n".encode("utf-8")))
        with self.Session() as db:
            result = asyncio.run(csv_route.csv_import_customers(file=upload, db=db, auth={"user_id": 1}))

        self.assertIn("created", result)

    def test_logo_upload_is_rate_limited_when_request_present(self):
        uploads_route = self._load_route_module("app.routes.uploads")

        with self.Session() as db:
            for _ in range(10):
                asyncio.run(
                    uploads_route.upload_logo(
                        file=UploadFile(
                            filename="logo.png",
                            file=BytesIO(PNG_BYTES),
                            headers=Headers({"content-type": "image/png"}),
                        ),
                        db=db,
                        auth={"user_id": 1},
                        request=make_request("127.0.0.1"),
                    )
                )

            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    uploads_route.upload_logo(
                        file=UploadFile(
                            filename="logo.png",
                            file=BytesIO(PNG_BYTES),
                            headers=Headers({"content-type": "image/png"}),
                        ),
                        db=db,
                        auth={"user_id": 1},
                        request=make_request("127.0.0.1"),
                    )
                )

        self.assertEqual(ctx.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()

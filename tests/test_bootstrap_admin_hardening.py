import os
import sys
import types
import unittest
from unittest import mock

from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


def make_request(host: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/bootstrap-admin",
        "headers": [],
        "client": (host, 12345),
        "server": ("testserver", 3001),
        "scheme": "http",
    }
    return Request(scope)


class BootstrapAdminHardeningTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_loopback_request_can_bootstrap_without_token(self):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest

        with self.Session() as db, mock.patch("app.routes.auth.BOOTSTRAP_ADMIN_TOKEN", ""):
            response = bootstrap_admin(
                BootstrapAdminRequest(
                    email="owner@example.com",
                    password="supersecret",
                    full_name="Owner User",
                ),
                db=db,
                request=make_request("127.0.0.1"),
            )

        self.assertEqual(response.user.email, "owner@example.com")
        self.assertEqual(response.user.membership.role_key, "owner")

    def test_remote_request_requires_bootstrap_token(self):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest

        with self.Session() as db, mock.patch("app.routes.auth.BOOTSTRAP_ADMIN_TOKEN", "setup-token"):
            with self.assertRaises(HTTPException) as ctx:
                bootstrap_admin(
                    BootstrapAdminRequest(
                        email="owner@example.com",
                        password="supersecret",
                        full_name="Owner User",
                    ),
                    db=db,
                    request=make_request("203.0.113.7"),
                    x_bootstrap_token=None,
                )

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("loopback", ctx.exception.detail.lower())

    def test_remote_request_with_valid_bootstrap_token_succeeds(self):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest

        with self.Session() as db, mock.patch("app.routes.auth.BOOTSTRAP_ADMIN_TOKEN", "setup-token"):
            response = bootstrap_admin(
                BootstrapAdminRequest(
                    email="owner@example.com",
                    password="supersecret",
                    full_name="Owner User",
                ),
                db=db,
                request=make_request("203.0.113.7"),
                x_bootstrap_token="setup-token",
            )

        self.assertEqual(response.user.email, "owner@example.com")

    def test_existing_in_process_calls_without_request_still_work(self):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest

        with self.Session() as db, mock.patch("app.routes.auth.BOOTSTRAP_ADMIN_TOKEN", "setup-token"):
            response = bootstrap_admin(
                BootstrapAdminRequest(
                    email="owner@example.com",
                    password="supersecret",
                    full_name="Owner User",
                ),
                db=db,
            )

        self.assertEqual(response.user.email, "owner@example.com")


if __name__ == "__main__":
    unittest.main()

import os
import sys
import types
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class AdminRbacProtectionTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _bootstrap_owner(self, db):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest
        from app.services.auth import require_permissions

        owner = bootstrap_admin(BootstrapAdminRequest(
            email="owner@example.com",
            password="supersecret",
            full_name="Owner User",
        ), db=db)
        owner_auth = require_permissions("users.manage")(db=db, authorization=f"Bearer {owner.token}")
        return owner, owner_auth

    def test_sensitive_admin_routes_require_specific_permissions(self):
        from fastapi import HTTPException
        from app.routes.auth import create_user, login
        from app.routes.settings import get_settings
        from app.routes.accounts import list_accounts
        from app.routes.audit import list_audit_logs
        from app.routes.companies import get_companies
        from app.routes.backups import list_backups
        from app.schemas.auth import LoginRequest, UserCreateRequest
        from app.services.auth import require_permissions

        with self.Session() as db:
            _owner, owner_auth = self._bootstrap_owner(db)
            create_user(UserCreateRequest(
                email="ops@example.com",
                password="opssecret1",
                full_name="Ops User",
                role_key="staff",
                allow_permissions=[
                    "settings.manage",
                    "accounts.view",
                    "audit.view",
                    "companies.view",
                    "backups.view",
                ],
                deny_permissions=[],
            ), db=db, auth=owner_auth)
            login_response = login(LoginRequest(email="ops@example.com", password="opssecret1"), db=db)
            token = login_response.token

            settings_auth = require_permissions("settings.manage")(db=db, authorization=f"Bearer {token}")
            accounts_auth = require_permissions("accounts.view")(db=db, authorization=f"Bearer {token}")
            audit_auth = require_permissions("audit.view")(db=db, authorization=f"Bearer {token}")
            companies_auth = require_permissions("companies.view")(db=db, authorization=f"Bearer {token}")
            backups_auth = require_permissions("backups.view")(db=db, authorization=f"Bearer {token}")

            self.assertIsInstance(get_settings(db=db, auth=settings_auth), dict)
            self.assertIsInstance(list_accounts(db=db, auth=accounts_auth), list)
            self.assertIsInstance(list_audit_logs(db=db, auth=audit_auth, limit=100, offset=0), list)
            self.assertIsInstance(get_companies(db=db, auth=companies_auth), list)
            self.assertIsInstance(list_backups(db=db, auth=backups_auth), list)

            with self.assertRaises(HTTPException) as denied_ctx:
                require_permissions("accounts.manage")(db=db, authorization=f"Bearer {token}")
            self.assertEqual(denied_ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()

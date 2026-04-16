import os
import sys
import types
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class AuthCompanyAccessControlTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_user_create_and_access_can_be_limited_to_selected_company_scopes(self):
        from app.models.companies import Company
        from app.routes.auth import bootstrap_admin, create_user, login
        from app.schemas.auth import BootstrapAdminRequest, LoginRequest, UserCreateRequest
        from app.services.auth import CURRENT_COMPANY_SCOPE, require_permissions

        with self.Session() as db:
            db.add(Company(name="Auckland Books", database_name="auckland_books"))
            db.commit()

            owner = bootstrap_admin(BootstrapAdminRequest(
                email="owner@example.com",
                password="supersecret",
                full_name="Owner User",
            ), db=db)
            owner_auth = require_permissions("users.manage")(db=db, authorization=f"Bearer {owner.token}")

            create_user(UserCreateRequest(
                email="ops@example.com",
                password="opssecret1",
                full_name="Ops User",
                role_key="staff",
                allow_permissions=["companies.view"],
                deny_permissions=[],
                company_scopes=[CURRENT_COMPANY_SCOPE],
            ), db=db, auth=owner_auth)

            login_response = login(LoginRequest(email="ops@example.com", password="opssecret1"), db=db)

            current_auth = require_permissions("companies.view")(
                db=db,
                authorization=f"Bearer {login_response.token}",
                x_company_database=None,
            )
            self.assertEqual(current_auth.user.email, "ops@example.com")

            with self.assertRaises(HTTPException) as ctx:
                require_permissions("companies.view")(
                    db=db,
                    authorization=f"Bearer {login_response.token}",
                    x_company_database="auckland_books",
                )
            self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()

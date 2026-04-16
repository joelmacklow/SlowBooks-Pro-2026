import os
import sys
import types
import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class PurchaseOrderDeliveryLocationTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _bootstrap_owner(self, db):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest

        return bootstrap_admin(BootstrapAdminRequest(
            email="owner@example.com",
            password="supersecret",
            full_name="Owner User",
        ), db=db)

    def _create_purchasing_user(self, db, owner_token):
        from app.routes.auth import create_user, login
        from app.schemas.auth import LoginRequest, UserCreateRequest
        from app.services.auth import require_permissions

        owner_auth = require_permissions("users.manage")(db=db, authorization=f"Bearer {owner_token}")
        create_user(UserCreateRequest(
            email="buyer@example.com",
            password="buyersecret",
            full_name="Buyer User",
            role_key="staff",
            allow_permissions=[
                "contacts.view",
                "purchasing.view",
                "purchasing.manage",
            ],
            deny_permissions=[],
        ), db=db, auth=owner_auth)
        return login(LoginRequest(email="buyer@example.com", password="buyersecret"), db=db)

    def test_list_delivery_locations_returns_company_and_admin_managed_locations(self):
        from app.routes.purchase_orders import list_delivery_locations
        from app.routes.settings import update_settings
        from app.services.auth import require_permissions

        with self.Session() as db:
            owner = self._bootstrap_owner(db)
            buyer = self._create_purchasing_user(db, owner.token)

            update_settings(
                {
                    "company_address1": "1 Queen Street",
                    "company_city": "Auckland",
                    "company_state": "Auckland",
                    "company_zip": "1010",
                    "purchase_order_delivery_locations": "Warehouse\n8 Depot Road\nWellington Wellington 6011",
                },
                db=db,
                auth=require_permissions("settings.manage")(db=db, authorization=f"Bearer {owner.token}"),
            )

            locations = list_delivery_locations(
                db=db,
                auth=require_permissions("purchasing.view")(db=db, authorization=f"Bearer {buyer.token}"),
            )

        self.assertEqual(
            locations,
            [
                {"label": "Company Main Address, 1 Queen Street, Auckland Auckland 1010", "value": "1 Queen Street\nAuckland Auckland 1010"},
                {"label": "Warehouse, 8 Depot Road, Wellington Wellington 6011", "value": "8 Depot Road\nWellington Wellington 6011"},
            ],
        )

    def test_create_po_rejects_unapproved_delivery_locations(self):
        from app.models.contacts import Vendor
        from app.routes.purchase_orders import create_po
        from app.routes.settings import update_settings
        from app.schemas.purchase_orders import POCreate, POLineCreate
        from app.services.auth import require_permissions

        with self.Session() as db:
            owner = self._bootstrap_owner(db)
            vendor = Vendor(name="Harbour Supplies")
            db.add(vendor)
            db.commit()

            update_settings(
                {
                    "company_address1": "1 Queen Street",
                    "company_city": "Auckland",
                    "company_state": "Auckland",
                    "company_zip": "1010",
                },
                db=db,
                auth=require_permissions("settings.manage")(db=db, authorization=f"Bearer {owner.token}"),
            )

            with self.assertRaises(HTTPException) as ctx:
                create_po(
                    POCreate(
                        vendor_id=vendor.id,
                        date=date(2026, 4, 17),
                        ship_to="99 Random Street\nAuckland Auckland 1010",
                        lines=[POLineCreate(description="Pens", quantity=1, rate=10)],
                    ),
                    db=db,
                    auth=require_permissions("purchasing.manage")(db=db, authorization=f"Bearer {owner.token}"),
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("approved delivery location", ctx.exception.detail.lower())

    def test_create_po_accepts_approved_delivery_location(self):
        from app.models.contacts import Vendor
        from app.routes.purchase_orders import create_po
        from app.routes.settings import update_settings
        from app.schemas.purchase_orders import POCreate, POLineCreate
        from app.services.auth import require_permissions

        with self.Session() as db:
            owner = self._bootstrap_owner(db)
            vendor = Vendor(name="Harbour Supplies")
            db.add(vendor)
            db.commit()

            update_settings(
                {
                    "company_address1": "1 Queen Street",
                    "company_city": "Auckland",
                    "company_state": "Auckland",
                    "company_zip": "1010",
                },
                db=db,
                auth=require_permissions("settings.manage")(db=db, authorization=f"Bearer {owner.token}"),
            )

            po = create_po(
                POCreate(
                    vendor_id=vendor.id,
                    date=date(2026, 4, 17),
                    ship_to="1 Queen Street\nAuckland Auckland 1010",
                    lines=[POLineCreate(description="Pens", quantity=1, rate=10)],
                ),
                db=db,
                auth=require_permissions("purchasing.manage")(db=db, authorization=f"Bearer {owner.token}"),
            )

        self.assertEqual(po.ship_to, "1 Queen Street\nAuckland Auckland 1010")

    def test_po_update_schema_accepts_date_fields(self):
        from app.schemas.purchase_orders import POUpdate

        payload = POUpdate.model_validate({
            "date": "2026-04-17",
            "expected_date": "2026-04-20",
        })

        self.assertEqual(payload.date, date(2026, 4, 17))
        self.assertEqual(payload.expected_date, date(2026, 4, 20))


if __name__ == "__main__":
    unittest.main()

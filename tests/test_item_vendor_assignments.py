import os
import sys
import types
import unittest
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class ItemVendorAssignmentTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_items_can_be_assigned_to_vendors_and_filtered(self):
        from app.models.contacts import Vendor
        from app.models.items import ItemType
        from app.routes.items import create_item, list_items, update_item
        from app.schemas.items import ItemCreate, ItemUpdate

        with self.Session() as db:
            vendor_a = Vendor(name="Harbour Supplies")
            vendor_b = Vendor(name="Office Goods")
            db.add_all([vendor_a, vendor_b])
            db.commit()
            db.refresh(vendor_a)
            db.refresh(vendor_b)

            pens = create_item(ItemCreate(
                name="Pens",
                item_type=ItemType.SERVICE,
                description="Blue pens",
                rate=Decimal("12.50"),
                cost=Decimal("7.25"),
                vendor_id=vendor_a.id,
            ), db=db)
            paper = create_item(ItemCreate(
                name="Paper",
                item_type=ItemType.MATERIAL,
                description="A4 ream",
                rate=Decimal("9.00"),
                cost=Decimal("4.50"),
                vendor_id=vendor_b.id,
            ), db=db)

            update_item(paper.id, ItemUpdate(vendor_id=vendor_a.id), db=db)

            vendor_a_items = list_items(vendor_id=vendor_a.id, db=db)
            vendor_b_items = list_items(vendor_id=vendor_b.id, db=db)

        self.assertEqual([item.name for item in vendor_a_items], ["Paper", "Pens"])
        self.assertEqual([item.vendor_id for item in vendor_a_items], [vendor_a.id, vendor_a.id])
        self.assertEqual(vendor_b_items, [])

    def test_item_codes_validate_and_search_by_code_or_name(self):
        from app.models.items import ItemType
        from app.routes.items import create_item, list_items
        from app.schemas.items import ItemCreate

        with self.assertRaises(ValidationError):
            ItemCreate(name="Bad Code", code="ABC-1", item_type=ItemType.SERVICE)

        with self.Session() as db:
            coded = create_item(ItemCreate(
                code="100-20",
                name="Pens",
                item_type=ItemType.SERVICE,
                description="Blue pens",
                rate=Decimal("12.50"),
                cost=Decimal("7.25"),
            ), db=db)
            uncoded = create_item(ItemCreate(
                name="Paper",
                item_type=ItemType.MATERIAL,
                description="A4 ream",
                rate=Decimal("9.00"),
                cost=Decimal("4.50"),
            ), db=db)

            by_code = list_items(search="100-20", db=db)
            by_name = list_items(search="Paper", db=db)

        self.assertEqual(coded.code, "100-20")
        self.assertIsNone(uncoded.code)
        self.assertEqual([item.name for item in by_code], ["Pens"])
        self.assertEqual([item.name for item in by_name], ["Paper"])


if __name__ == "__main__":
    unittest.main()

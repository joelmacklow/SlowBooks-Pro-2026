import os
import unittest
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base


class GstCodeTests(unittest.TestCase):
    def setUp(self):
        from app.models.gst import GstCode

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.GstCode = GstCode

    def test_model_defaults_and_seeded_codes(self):
        from app.models.gst import ensure_default_gst_codes

        code = self.GstCode(code="TEST", name="Test", category="taxable")
        self.assertEqual(code.rate, Decimal("0"))
        self.assertTrue(code.is_active)
        self.assertFalse(code.is_system)

        with self.Session() as db:
            ensure_default_gst_codes(db)
            rows = db.query(self.GstCode).order_by(self.GstCode.sort_order).all()

        self.assertEqual([row.code for row in rows], ["GST15", "ZERO", "EXEMPT", "NO_GST"])
        self.assertEqual(rows[0].rate, Decimal("0.1500"))
        self.assertEqual(rows[0].category, "taxable")
        self.assertEqual(rows[1].category, "zero_rated")
        self.assertEqual(rows[2].category, "exempt")
        self.assertEqual(rows[3].category, "no_gst")
        self.assertTrue(all(row.is_system for row in rows))

    def test_default_seed_is_idempotent(self):
        from app.models.gst import ensure_default_gst_codes

        with self.Session() as db:
            ensure_default_gst_codes(db)
            ensure_default_gst_codes(db)
            count = db.query(self.GstCode).count()

        self.assertEqual(count, 4)

    def test_list_gst_codes_returns_active_codes_in_order(self):
        from app.models.gst import ensure_default_gst_codes
        from app.routes.gst import list_gst_codes

        with self.Session() as db:
            ensure_default_gst_codes(db)
            db.query(self.GstCode).filter(self.GstCode.code == "EXEMPT").one().is_active = False
            db.commit()
            rows = list_gst_codes(db=db)

        self.assertEqual([row.code for row in rows], ["GST15", "ZERO", "NO_GST"])

    def test_get_gst_code_returns_code_by_code(self):
        from app.models.gst import ensure_default_gst_codes
        from app.routes.gst import get_gst_code

        with self.Session() as db:
            ensure_default_gst_codes(db)
            code = get_gst_code("GST15", db=db)

        self.assertEqual(code.code, "GST15")
        self.assertEqual(code.rate, Decimal("0.1500"))

    def test_get_gst_code_raises_404_for_unknown_code(self):
        from app.models.gst import ensure_default_gst_codes
        from app.routes.gst import get_gst_code

        with self.Session() as db:
            ensure_default_gst_codes(db)
            with self.assertRaises(HTTPException) as ctx:
                get_gst_code("MISSING", db=db)

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()

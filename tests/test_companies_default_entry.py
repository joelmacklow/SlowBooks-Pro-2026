import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base


class CompaniesDefaultEntryTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_get_companies_includes_default_company_entry(self):
        from app.models.companies import Company
        from app.models.settings import Settings
        from app.routes.companies import get_companies

        with self.Session() as db:
            db.add(Settings(key="company_name", value="SlowBooks NZ"))
            db.add(Company(name="Auckland Books", database_name="auckland_books", description="NZ demo company"))
            db.commit()

            companies = get_companies(db=db, auth=None)

        self.assertEqual(companies[0]["name"], "SlowBooks NZ")
        self.assertTrue(companies[0]["is_default"])
        self.assertEqual(companies[0]["description"], "Default company")
        self.assertEqual(companies[1]["database_name"], "auckland_books")


if __name__ == "__main__":
    unittest.main()

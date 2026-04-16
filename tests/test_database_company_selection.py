import os
import unittest
from unittest import mock

os.environ["DATABASE_URL"] = "sqlite:////tmp/slowbooks_master.db"

import app.database as database


class DatabaseCompanySelectionTests(unittest.TestCase):
    def test_database_url_for_company_rewrites_sqlite_file_path(self):
        with mock.patch.object(database, "DATABASE_URL", "sqlite:////tmp/slowbooks_master.db"):
            self.assertEqual(
                database._database_url_for_company("auckland_books"),
                "sqlite:////tmp/auckland_books.db",
            )

    def test_database_url_for_company_preserves_default_when_no_company_selected(self):
        with mock.patch.object(database, "DATABASE_URL", "postgresql://bookkeeper:bookkeeper@db:5432/bookkeeper"):
            self.assertEqual(
                database._database_url_for_company(None),
                "postgresql://bookkeeper:bookkeeper@db:5432/bookkeeper",
            )


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest import mock
from types import SimpleNamespace

from fastapi import HTTPException

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

    def test_authorized_company_database_ignores_scoped_header_without_valid_auth(self):
        with mock.patch("app.services.auth.get_auth_context", return_value=None):
            self.assertIsNone(database._authorized_company_database("auckland_books", authorization=None))

    def test_authorized_company_database_returns_membership_scope_for_valid_auth(self):
        context = SimpleNamespace(membership=SimpleNamespace(company_scope="auckland_books"))
        with mock.patch("app.services.auth.get_auth_context", return_value=context):
            self.assertEqual(
                database._authorized_company_database("auckland_books", authorization="Bearer token"),
                "auckland_books",
            )

    def test_authorized_company_database_rejects_invalid_scoped_access(self):
        with mock.patch("app.services.auth.get_auth_context", side_effect=HTTPException(status_code=403, detail="forbidden")):
            with self.assertRaises(HTTPException) as ctx:
                database._authorized_company_database("auckland_books", authorization="Bearer token")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_get_db_uses_default_session_when_scoped_header_is_not_authorized(self):
        session = mock.Mock()
        factory = mock.Mock(return_value=session)
        with mock.patch.object(database, "_authorized_company_database", return_value=None), \
             mock.patch.object(database, "_session_factory_for_company", return_value=factory) as session_factory:
            generator = database.get_db(x_company_database="auckland_books", authorization=None)
            try:
                self.assertIs(next(generator), session)
            finally:
                try:
                    next(generator)
                except StopIteration:
                    pass

        session_factory.assert_called_once_with(None)
        session.close.assert_called_once()

    def test_get_db_uses_authorized_company_session_when_scope_is_valid(self):
        session = mock.Mock()
        factory = mock.Mock(return_value=session)
        with mock.patch.object(database, "_authorized_company_database", return_value="auckland_books"), \
             mock.patch.object(database, "_session_factory_for_company", return_value=factory) as session_factory:
            generator = database.get_db(x_company_database="auckland_books", authorization="Bearer token")
            try:
                self.assertIs(next(generator), session)
            finally:
                try:
                    next(generator)
                except StopIteration:
                    pass

        session_factory.assert_called_once_with("auckland_books")
        session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

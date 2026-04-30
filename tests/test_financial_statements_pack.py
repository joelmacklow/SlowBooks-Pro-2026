import inspect
import json
import os
import sys
import types
import unittest
from datetime import date
from io import BytesIO
from unittest import mock
import zipfile

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class FinancialStatementsPackTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401
        from app.routes.auth import bootstrap_admin, create_user, login
        from app.schemas.auth import BootstrapAdminRequest, LoginRequest, UserCreateRequest
        from app.services.auth import require_permissions

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

        with self.Session() as db:
            owner = bootstrap_admin(
                BootstrapAdminRequest(
                    email="owner@example.com",
                    password="supersecret",
                    full_name="Owner User",
                ),
                db=db,
            )
            owner_auth = require_permissions("users.manage")(db=db, authorization=f"Bearer {owner.token}")
            create_user(
                UserCreateRequest(
                    email="staff@example.com",
                    password="staffsecret",
                    full_name="Staff User",
                    role_key="staff",
                    allow_permissions=["accounts.view"],
                    deny_permissions=[],
                ),
                db=db,
                auth=owner_auth,
            )
            staff = login(LoginRequest(email="staff@example.com", password="staffsecret"), db=db)
            db.commit()

            self.owner_token = owner.token
            self.staff_token = staff.token

        from app.routes import reports as reports_route
        self.reports_route = reports_route

    def _auth_dependency(self, func):
        parameter = inspect.signature(func).parameters.get("auth")
        self.assertIsNotNone(parameter, f"{func.__name__} is missing auth parameter")
        dependency = getattr(parameter.default, "dependency", None)
        self.assertIsNotNone(dependency, f"{func.__name__} auth parameter is not a FastAPI dependency")
        return dependency

    def test_pack_route_requires_accounts_manage(self):
        dependency = self._auth_dependency(self.reports_route.financial_statements_pack)
        with self.Session() as db:
            with self.assertRaises(HTTPException) as unauth_ctx:
                dependency(db=db, authorization=None)
            self.assertEqual(unauth_ctx.exception.status_code, 401)

            with self.assertRaises(HTTPException) as staff_ctx:
                dependency(db=db, authorization=f"Bearer {self.staff_token}")
            self.assertEqual(staff_ctx.exception.status_code, 403)

            owner_auth = dependency(db=db, authorization=f"Bearer {self.owner_token}")

        self.assertIsNotNone(owner_auth)

    def test_pack_route_returns_archive_with_manifest_and_expected_documents(self):
        with mock.patch.object(self.reports_route, "generate_report_pdf", side_effect=lambda **kwargs: f"%PDF-{kwargs['title']}".encode("utf-8")), \
             mock.patch.object(self.reports_route, "generate_gst101a_pdf", return_value=b"%PDF-GST101A"), \
             mock.patch.object(self.reports_route, "fixed_assets_reconciliation_report", return_value={
                 "as_of_date": "2026-04-30",
                 "assets": [],
                 "total_cost": 0,
                 "total_accumulated_depreciation": 0,
                 "total_book_value": 0,
             }):
            with self.Session() as db:
                owner_auth = self._auth_dependency(self.reports_route.financial_statements_pack)(
                    db=db, authorization=f"Bearer {self.owner_token}"
                )
                response = self.reports_route.financial_statements_pack(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 4, 30),
                    db=db,
                    auth=owner_auth,
                )

        self.assertEqual(response.media_type, "application/zip")
        self.assertEqual(
            response.headers["Content-Disposition"],
            'attachment; filename="FinancialStatementsPack_2026-04-01_2026-04-30.zip"',
        )

        archive = zipfile.ZipFile(BytesIO(response.body))
        names = set(archive.namelist())
        expected_names = {
            "manifest.json",
            "statements/ProfitLoss_2026-04-01_2026-04-30.pdf",
            "statements/BalanceSheet_2026-04-30.pdf",
            "statements/TrialBalance_2026-04-30.pdf",
            "statements/CashFlow_2026-04-01_2026-04-30.pdf",
            "ledger/GeneralLedger_2026-04-01_2026-04-30.pdf",
            "aging/ARAging_2026-04-30.pdf",
            "aging/APAging_2026-04-30.pdf",
            "gst/GST101A_2026-04-01_2026-04-30.pdf",
            "fixed-assets/FixedAssetReconciliation_2026-04-30.pdf",
            "equity/StatementOfChangesInEquity_2026-04-01_2026-04-30.pdf",
            "policies/AccountingPolicies_2026-04-30.pdf",
            "directors/DirectorsApproval_2026-04-30.pdf",
        }
        self.assertSetEqual(names, expected_names)

        manifest = json.loads(archive.read("manifest.json"))
        self.assertEqual(manifest["pack_type"], "financial_statements_pack")
        self.assertEqual(manifest["status"], "partial")
        self.assertEqual(manifest["period"], {"start_date": "2026-04-01", "end_date": "2026-04-30"})
        self.assertEqual(len(manifest["included_documents"]), 12)
        self.assertIn("notes_to_financial_statements", manifest["missing_document_categories"])
        self.assertIn("tax_fixed_asset_schedule", manifest["missing_document_categories"])

        included_paths = {entry["path"] for entry in manifest["included_documents"]}
        self.assertSetEqual(included_paths, expected_names - {"manifest.json"})
        fixed_asset_entry = next(entry for entry in manifest["included_documents"] if entry["label"] == "Fixed Asset Reconciliation")
        self.assertEqual(fixed_asset_entry["media_type"], "application/pdf")
        soce_entry = next(entry for entry in manifest["included_documents"] if entry["label"] == "Statement of Changes in Equity")
        policies_entry = next(entry for entry in manifest["included_documents"] if entry["label"] == "Accounting Policies")
        directors_entry = next(entry for entry in manifest["included_documents"] if entry["label"] == "Directors Approval and Signatures")
        self.assertEqual(soce_entry["media_type"], "application/pdf")
        self.assertEqual(policies_entry["media_type"], "application/pdf")
        self.assertEqual(directors_entry["media_type"], "application/pdf")

        self.assertEqual(archive.read("statements/ProfitLoss_2026-04-01_2026-04-30.pdf"), b"%PDF-Profit & Loss")
        self.assertEqual(archive.read("gst/GST101A_2026-04-01_2026-04-30.pdf"), b"%PDF-GST101A")
        self.assertEqual(archive.read("fixed-assets/FixedAssetReconciliation_2026-04-30.pdf"), b"%PDF-Fixed Asset Reconciliation")
        self.assertEqual(archive.read("equity/StatementOfChangesInEquity_2026-04-01_2026-04-30.pdf"), b"%PDF-Statement of Changes in Equity")
        self.assertEqual(archive.read("policies/AccountingPolicies_2026-04-30.pdf"), b"%PDF-Accounting Policies")
        self.assertEqual(archive.read("directors/DirectorsApproval_2026-04-30.pdf"), b"%PDF-Directors' Approval and Signatures")


if __name__ == "__main__":
    unittest.main()

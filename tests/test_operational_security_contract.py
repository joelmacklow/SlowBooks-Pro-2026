import inspect
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

RATE_LIMIT_EXPECTATIONS = {
    "app.routes.auth": ["bootstrap_admin", "login"],
    "app.routes.backups": ["make_backup", "download_backup", "restore"],
    "app.routes.settings": ["test_email"],
    "app.routes.uploads": ["upload_logo"],
    "app.routes.csv": [
        "csv_import_customers",
        "csv_import_vendors",
        "csv_import_items",
    ],
    "app.routes.iif": ["import_iif", "validate_iif_file"],
    "app.routes.bank_import": ["preview_statement", "import_statement"],
    "app.routes.xero_import": ["dry_run_xero_import", "import_xero_bundle"],
    "app.routes.invoices": ["email_invoice"],
    "app.routes.estimates": ["email_estimate"],
    "app.routes.credit_memos": ["email_credit_memo"],
    "app.routes.purchase_orders": ["email_purchase_order"],
    "app.routes.payroll": ["email_payroll_payslip"],
    "app.routes.reports": ["email_customer_statement"],
}

UPLOAD_LIMIT_EXPECTATIONS = {
    "app.routes.uploads": ["upload_logo"],
    "app.routes.csv": [
        "_read_csv_upload",
    ],
    "app.routes.iif": ["import_iif", "validate_iif_file"],
    "app.routes.bank_import": ["preview_statement", "import_statement"],
    "app.routes.xero_import": ["_load_files"],
}


class OperationalSecurityContractTests(unittest.TestCase):
    @staticmethod
    def _import_module(module_name: str):
        sys.modules.pop(module_name, None)
        with mock.patch("fastapi.dependencies.utils.ensure_multipart_is_installed", return_value=None):
            return __import__(module_name, fromlist=["*"])

    def _assert_function_source_contains(self, module_name: str, function_name: str, needle: str):
        module = self._import_module(module_name)
        func = getattr(module, function_name)
        source = inspect.getsource(func)
        self.assertIn(
            needle,
            source,
            f"{module_name}.{function_name} no longer contains expected safeguard marker {needle!r}",
        )

    def test_rate_limited_endpoints_keep_rate_limit_hooks(self):
        for module_name, function_names in RATE_LIMIT_EXPECTATIONS.items():
            for function_name in function_names:
                with self.subTest(module=module_name, function=function_name):
                    self._assert_function_source_contains(module_name, function_name, "enforce_rate_limit(")

    def test_file_ingest_endpoints_keep_upload_size_checks(self):
        for module_name, function_names in UPLOAD_LIMIT_EXPECTATIONS.items():
            for function_name in function_names:
                with self.subTest(module=module_name, function=function_name):
                    self._assert_function_source_contains(module_name, function_name, "enforce_upload_size(")

    def test_bootstrap_admin_route_keeps_remote_trust_gate_and_header_token(self):
        module = self._import_module("app.routes.auth")
        bootstrap_source = inspect.getsource(module.bootstrap_admin)

        self.assertIn("_enforce_bootstrap_request_trust(", bootstrap_source)
        self.assertIn('alias="X-Bootstrap-Token"', bootstrap_source)

    def test_settings_client_masking_keeps_operational_secrets_blank(self):
        module = self._import_module("app.routes.settings")
        masked = module._settings_for_client(
            {
                "company_name": "Demo Co",
                "closing_date_password": "secret-one",
                "smtp_password": "secret-two",
            }
        )

        self.assertEqual(masked["company_name"], "Demo Co")
        self.assertEqual(masked["closing_date_password"], "")
        self.assertEqual(masked["smtp_password"], "")

    def test_cors_contract_stays_explicit_and_non_wildcard(self):
        import app.config as config

        self.assertEqual(
            config.resolve_cors_origins(env={}),
            ["http://localhost:3001", "http://127.0.0.1:3001"],
        )
        self.assertNotIn("*", config.resolve_cors_origins(env={}))

        main_source = Path("app/main.py").read_text()
        self.assertIn("allow_origins=CORS_ALLOW_ORIGINS", main_source)
        self.assertNotIn('allow_origins=["*"]', main_source)

    def test_main_app_sets_browser_security_headers(self):
        main_source = Path("app/main.py").read_text()
        self.assertIn("add_security_headers", main_source)
        self.assertIn("X-Content-Type-Options", main_source)
        self.assertIn("X-Frame-Options", main_source)
        self.assertIn("Content-Security-Policy", main_source)
        self.assertIn("Strict-Transport-Security", main_source)

    def test_smtp_settings_are_environment_owned(self):
        settings_source = Path("app/routes/settings.py").read_text()
        email_source = Path("app/services/email_service.py").read_text()
        self.assertIn("SMTP_SETTING_KEYS", settings_source)
        self.assertIn("key in SMTP_SETTING_KEYS", settings_source)
        self.assertIn("SMTP_HOST", email_source)
        self.assertNotIn("db.query(Settings).filter(Settings.key.in_(keys))", email_source)


if __name__ == "__main__":
    unittest.main()

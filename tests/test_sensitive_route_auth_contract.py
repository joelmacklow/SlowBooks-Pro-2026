import inspect
import os
import sys
import types
import unittest
from unittest import mock

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)


EXPECTED_ROUTE_AUTH = {
    "app.routes.auth": {
        "bootstrap_admin": ("public", None),
        "login": ("public", None),
        "logout": ("permissions", ()),
        "me": ("optional_auth", None),
        "auth_meta": ("permissions", ("users.manage",)),
        "list_users": ("permissions", ("users.manage",)),
        "create_user": ("permissions", ("users.manage",)),
        "update_user": ("permissions", ("users.manage",)),
    },
    "app.routes.backups": {
        "list_backups": ("permissions", ("backups.view",)),
        "make_backup": ("permissions", ("backups.manage",)),
        "download_backup": ("permissions", ("backups.view",)),
        "restore": ("permissions", ("backups.manage",)),
    },
    "app.routes.companies": {
        "get_companies": ("permissions", ("companies.view",)),
        "new_company": ("permissions", ("companies.manage",)),
    },
    "app.routes.csv": {
        "csv_export_customers": ("permissions", ("import_export.view",)),
        "csv_export_vendors": ("permissions", ("import_export.view",)),
        "csv_export_items": ("permissions", ("import_export.view",)),
        "csv_export_invoices": ("permissions", ("import_export.view",)),
        "csv_export_accounts": ("permissions", ("import_export.view",)),
        "csv_import_customers": ("permissions", ("import_export.manage",)),
        "csv_import_vendors": ("permissions", ("import_export.manage",)),
        "csv_import_items": ("permissions", ("import_export.manage",)),
    },
    "app.routes.iif": {
        "export_all_iif": ("permissions", ("import_export.view",)),
        "export_accounts_iif": ("permissions", ("import_export.view",)),
        "export_customers_iif": ("permissions", ("import_export.view",)),
        "export_vendors_iif": ("permissions", ("import_export.view",)),
        "export_items_iif": ("permissions", ("import_export.view",)),
        "export_invoices_iif": ("permissions", ("import_export.view",)),
        "export_payments_iif": ("permissions", ("import_export.view",)),
        "export_estimates_iif": ("permissions", ("import_export.view",)),
        "import_iif": ("permissions", ("import_export.manage",)),
        "validate_iif_file": ("permissions", ("import_export.manage",)),
    },
    "app.routes.uploads": {
        "upload_logo": ("permissions", ("settings.manage",)),
    },
    "app.routes.bank_import": {
        "preview_statement": ("permissions", ("banking.manage",)),
        "import_statement": ("permissions", ("banking.manage",)),
    },
    "app.routes.xero_import": {
        "dry_run_xero_import": ("permissions", ("accounts.manage",)),
        "import_xero_bundle": ("permissions", ("accounts.manage",)),
    },
    "app.routes.settings": {
        "get_public_settings": ("public", None),
        "get_settings": ("permissions", ("settings.manage",)),
        "update_settings": ("permissions", ("settings.manage",)),
        "list_invoice_reminder_rules": ("permissions", ("settings.manage",)),
        "create_invoice_reminder_rule": ("permissions", ("settings.manage",)),
        "update_invoice_reminder_rule": ("permissions", ("settings.manage",)),
        "delete_invoice_reminder_rule": ("permissions", ("settings.manage",)),
        "test_email": ("permissions", ("settings.manage",)),
        "load_chart_template": ("permissions", ("settings.manage",)),
        "load_demo_data": ("permissions", ("settings.manage",)),
    },
    "app.routes.reports": {
        "profit_loss": ("permissions", ("accounts.manage",)),
        "profit_loss_pdf": ("permissions", ("accounts.manage",)),
        "balance_sheet": ("permissions", ("accounts.manage",)),
        "balance_sheet_pdf": ("permissions", ("accounts.manage",)),
        "trial_balance": ("permissions", ("accounts.manage",)),
        "trial_balance_pdf": ("permissions", ("accounts.manage",)),
        "cash_flow_report": ("permissions", ("accounts.manage",)),
        "cash_flow_pdf": ("permissions", ("accounts.manage",)),
        "ar_aging": ("permissions", ("accounts.manage",)),
        "ar_aging_pdf": ("permissions", ("accounts.manage",)),
        "gst_return_report": ("permissions", ("accounts.manage",)),
        "gst_returns_overview": ("permissions", ("accounts.manage",)),
        "gst_return_transactions": ("permissions", ("accounts.manage",)),
        "confirm_gst_return": ("permissions", ("accounts.manage",)),
        "confirm_gst_settlement": ("permissions", ("accounts.manage",)),
        "sales_tax_report": ("permissions", ("accounts.manage",)),
        "gst_return_pdf": ("permissions", ("accounts.manage",)),
        "general_ledger": ("permissions", ("accounts.manage",)),
        "general_ledger_pdf": ("permissions", ("accounts.manage",)),
        "income_by_customer": ("permissions", ("accounts.manage",)),
        "income_by_customer_pdf": ("permissions", ("accounts.manage",)),
        "ap_aging": ("permissions", ("accounts.manage",)),
        "ap_aging_pdf": ("permissions", ("accounts.manage",)),
        "customer_statement_pdf": ("permissions", ("accounts.manage",)),
        "email_customer_statement": ("permissions", ("accounts.manage",)),
        "overdue_statement_candidates": ("permissions", ("accounts.manage",)),
        "invoice_reminder_preview": ("permissions", ("accounts.manage",)),
        "send_overdue_statements": ("permissions", ("accounts.manage",)),
    },
    "app.routes.employees": {
        "list_employees": ("permissions", ("employees.view_private",)),
        "get_employee": ("permissions", ("employees.view_private",)),
        "create_employee": ("permissions", ("employees.manage",)),
        "update_employee": ("permissions", ("employees.manage",)),
        "export_starter_employee_filing": ("permissions", ("employees.filing.export",)),
        "export_leaver_employee_filing": ("permissions", ("employees.filing.export",)),
        "get_employee_filing_history": ("permissions", ("employees.view_private",)),
        "update_employee_filing_record": ("permissions", ("employees.filing.export",)),
    },
    "app.routes.payroll": {
        "list_pay_runs": ("permissions", ("payroll.view",)),
        "get_pay_run": ("permissions", ("payroll.view",)),
        "create_pay_run": ("permissions", ("payroll.create",)),
        "process_pay_run": ("permissions", ("payroll.process",)),
        "payroll_payslip_pdf": ("permissions", ("payroll.payslips.view",)),
        "email_payroll_payslip": ("permissions", ("payroll.payslips.email",)),
        "export_employment_information": ("permissions", ("payroll.filing.export",)),
        "get_pay_run_filing_history": ("permissions", ("payroll.view",)),
        "update_pay_run_filing_record": ("permissions", ("payroll.filing.export",)),
    },
    "app.routes.invoices": {
        "list_invoices": ("permissions", ("sales.view",)),
        "get_invoice": ("permissions", ("sales.view",)),
        "create_invoice": ("permissions", ("sales.manage",)),
        "update_invoice": ("permissions", ("sales.manage",)),
        "invoice_pdf": ("permissions", ("sales.view",)),
        "void_invoice": ("permissions", ("sales.manage",)),
        "mark_invoice_sent": ("permissions", ("sales.manage",)),
        "email_invoice": ("permissions", ("sales.manage",)),
        "duplicate_invoice": ("permissions", ("sales.manage",)),
    },
    "app.routes.estimates": {
        "list_estimates": ("permissions", ("sales.view",)),
        "get_estimate": ("permissions", ("sales.view",)),
        "create_estimate": ("permissions", ("sales.manage",)),
        "update_estimate": ("permissions", ("sales.manage",)),
        "estimate_pdf": ("permissions", ("sales.view",)),
        "email_estimate": ("permissions", ("sales.manage",)),
        "convert_to_invoice": ("permissions", ("sales.manage",)),
    },
    "app.routes.credit_memos": {
        "list_credit_memos": ("permissions", ("sales.view",)),
        "get_credit_memo": ("permissions", ("sales.view",)),
        "create_credit_memo": ("permissions", ("sales.manage",)),
        "update_credit_memo": ("permissions", ("sales.manage",)),
        "credit_memo_pdf": ("permissions", ("sales.view",)),
        "email_credit_memo": ("permissions", ("sales.manage",)),
        "apply_credit": ("permissions", ("sales.manage",)),
    },
    "app.routes.purchase_orders": {
        "list_pos": ("permissions", ("purchasing.view",)),
        "list_delivery_locations": ("permissions", ("purchasing.view",)),
        "get_po": ("permissions", ("purchasing.view",)),
        "create_po": ("permissions", ("purchasing.manage",)),
        "update_po": ("permissions", ("purchasing.manage",)),
        "purchase_order_pdf": ("permissions", ("purchasing.view",)),
        "email_purchase_order": ("permissions", ("purchasing.manage",)),
        "convert_to_bill": ("permissions", ("purchasing.manage",)),
    },
}


class SensitiveRouteAuthContractTests(unittest.TestCase):
    def _extract_permission_tuple(self, dependency) -> tuple[str, ...] | None:
        closure = getattr(dependency, "__closure__", None) or ()
        for cell in closure:
            value = cell.cell_contents
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
        return None

    def test_sensitive_routes_keep_expected_auth_contracts(self):
        for module_name, expectations in EXPECTED_ROUTE_AUTH.items():
            sys.modules.pop(module_name, None)
            with mock.patch("fastapi.dependencies.utils.ensure_multipart_is_installed", return_value=None):
                module = __import__(module_name, fromlist=["*"])
            for function_name, (kind, expected) in expectations.items():
                func = getattr(module, function_name)
                sig = inspect.signature(func)
                auth_param = sig.parameters.get("auth")

                if kind == "public":
                    self.assertIsNone(auth_param, f"{module_name}.{function_name} unexpectedly gained auth")
                    continue

                self.assertIsNotNone(auth_param, f"{module_name}.{function_name} is missing auth")
                dependency = getattr(auth_param.default, "dependency", None)
                self.assertIsNotNone(dependency, f"{module_name}.{function_name} auth is not a FastAPI dependency")

                if kind == "optional_auth":
                    self.assertEqual(dependency.__name__, "get_optional_auth_context")
                    continue

                self.assertEqual(dependency.__name__, "dependency", f"{module_name}.{function_name} should use require_permissions")
                self.assertEqual(self._extract_permission_tuple(dependency), expected, f"{module_name}.{function_name} permission drifted")


if __name__ == "__main__":
    unittest.main()

# ============================================================================
# Decompiled from qbw32.exe!CCompanyInfo + CQBPreferences
# Offset: 0x00241200 / 0x0023F000
# Original stored company info in the .QBW file header (bytes 0x40-0x1FF)
# encrypted with a simple XOR 0x1F cipher. Preferences lived in the registry
# at HKCU\Software\Intuit\QuickBooks\12.0\Preferences.
# ============================================================================

from sqlalchemy import Column, Integer, String, Numeric, DateTime, func

from app.database import Base
from app.services.payment_terms import DEFAULT_PAYMENT_TERMS_CONFIG


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Default settings keys
DEFAULT_SETTINGS = {
    "company_name": "My Company",
    "company_address1": "",
    "company_address2": "",
    "company_city": "",
    "company_state": "",
    "company_zip": "",
    "company_phone": "",
    "company_email": "",
    "company_website": "",
    "company_tax_id": "",
    "default_terms": "Net 30",
    "payment_terms_config": DEFAULT_PAYMENT_TERMS_CONFIG,
    "default_tax_rate": "0.0",
    "invoice_prefix": "",
    "invoice_next_number": "1001",
    "estimate_prefix": "E-",
    "estimate_next_number": "1001",
    "credit_memo_prefix": "CM-",
    "credit_memo_next_number": "0001",
    "purchase_order_prefix": "PO-",
    "purchase_order_next_number": "0001",
    "invoice_notes": "Thank you for your business.",
    "invoice_footer": "",
    # Feature 10: Closing Date Enforcement
    "closing_date": "",
    "closing_date_password": "",
    # Feature 8: SMTP Email
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from_email": "",
    "smtp_from_name": "",
    "smtp_use_tls": "true",
    "purchase_order_delivery_locations": "",
    # Feature 15: Company Logo
    "company_logo_path": "",
    # NZ localization foundation
    "country": "NZ",
    "tax_regime": "NZ",
    "currency": "NZD",
    "locale": "en-NZ",
    "timezone": "Pacific/Auckland",
    "ird_number": "",
    "gst_number": "",
    "gst_registered": "false",
    "gst_basis": "invoice",
    "gst_period": "two-monthly",
    "prices_include_gst": "false",
    "financial_year_start": "",
    "financial_year_end": "",
    "payroll_contact_name": "",
    "payroll_contact_phone": "",
    "payroll_contact_email": "",
    "system_account_accounts_receivable_id": "",
    "system_account_accounts_payable_id": "",
    "system_account_gst_control_id": "",
    "system_account_undeposited_funds_id": "",
    "system_account_default_sales_income_id": "",
    "system_account_default_expense_id": "",
    "system_account_default_bank_id": "",
    "system_account_wages_expense_id": "",
    "system_account_employer_kiwisaver_expense_id": "",
    "system_account_paye_payable_id": "",
    "system_account_kiwisaver_payable_id": "",
    "system_account_esct_payable_id": "",
    "system_account_child_support_payable_id": "",
    "system_account_payroll_clearing_id": "",
    "chart_setup_source": "",
    "chart_setup_ready_at": "",
}

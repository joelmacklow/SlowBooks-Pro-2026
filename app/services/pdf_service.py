# ============================================================================
# Decompiled from qbw32.exe!CPrintManager + CInvoicePrintLayout
# Offset: 0x00220000
# Original used Crystal Reports 8.5 OCX embedded in an OLE container for
# print preview. The .RPT template files were stored as RT_RCDATA resources.
# We're using WeasyPrint + Jinja2 because Crystal Reports can go to hell.
# ============================================================================

from pathlib import Path
from io import BytesIO
from datetime import date
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, pass_context
from weasyprint import HTML

from app.config import UPLOADS_DIR
from app.services.formatting import format_currency, format_date

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
STATIC_DIR = Path(__file__).parent.parent / "static"
_jinja_env = Environment(autoescape=True, loader=FileSystemLoader(str(TEMPLATE_DIR)))


@pass_context
def _format_currency(context, value):
    return format_currency(value, context.get("company", {}))


@pass_context
def _format_date(context, value):
    return format_date(value, context.get("company", {}))


_jinja_env.filters["currency"] = _format_currency
_jinja_env.filters["fdate"] = _format_date


def _resolve_static_asset_uri(path_value: str | None) -> str | None:
    raw = str(path_value or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https", "file", "data"):
        return raw
    if raw.startswith("/static/uploads/"):
        candidate = Path(UPLOADS_DIR) / raw.split("/static/uploads/", 1)[1]
        if candidate.exists():
            return candidate.as_uri()
    if raw.startswith("/static/"):
        candidate = STATIC_DIR / raw.split("/static/", 1)[1]
        if candidate.exists():
            return candidate.as_uri()
    return raw


def _template_company_settings(company_settings: dict | None) -> dict:
    company = dict(company_settings or {})
    company["company_logo_src"] = _resolve_static_asset_uri(company.get("company_logo_path"))
    return company


def generate_invoice_pdf(invoice, company_settings: dict) -> bytes:
    template = _jinja_env.get_template("invoice_pdf.html")
    html_str = template.render(inv=invoice, company=_template_company_settings(company_settings))
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR.parent)).write_pdf()


def generate_estimate_pdf(estimate, company_settings: dict) -> bytes:
    template = _jinja_env.get_template("estimate_pdf.html")
    html_str = template.render(est=estimate, company=_template_company_settings(company_settings))
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR.parent)).write_pdf()


def generate_credit_memo_pdf(credit_memo, company_settings: dict) -> bytes:
    template = _jinja_env.get_template("credit_memo_pdf.html")
    html_str = template.render(cm=credit_memo, company=_template_company_settings(company_settings))
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR.parent)).write_pdf()


def generate_purchase_order_pdf(purchase_order, company_settings: dict) -> bytes:
    template = _jinja_env.get_template("purchase_order_pdf.html")
    html_str = template.render(po=purchase_order, company=_template_company_settings(company_settings))
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR.parent)).write_pdf()


def generate_statement_pdf(customer, invoices, payments, company_settings: dict, as_of_date=None) -> bytes:
    template = _jinja_env.get_template("statement_pdf.html")
    html_str = template.render(
        customer=customer, invoices=invoices, payments=payments,
        company=_template_company_settings(company_settings), as_of_date=as_of_date,
    )
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR.parent)).write_pdf()


def generate_payroll_payslip_pdf(pay_run, stub, employee, company_settings: dict) -> bytes:
    template = _jinja_env.get_template("payroll_payslip_pdf.html")
    html_str = template.render(
        pay_run=pay_run,
        stub=stub,
        employee=employee,
        company=_template_company_settings(company_settings),
    )
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR.parent)).write_pdf()


def generate_report_pdf(
    *,
    title: str,
    company_settings: dict,
    subtitle: str = "",
    tables: list[dict] | None = None,
    landscape: bool = False,
) -> bytes:
    template = _jinja_env.get_template("report_pdf.html")
    html_str = template.render(
        title=title,
        company=_template_company_settings(company_settings),
        subtitle=subtitle,
        tables=tables or [],
        landscape=landscape,
        generated_on=date.today(),
    )
    return HTML(string=html_str, base_url=str(TEMPLATE_DIR.parent)).write_pdf()

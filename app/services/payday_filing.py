import csv
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO

from app.models.payroll import PayRun


PACKAGE_VERSION_IDENTIFIER = "SlowBooksNZ_nz-localization_v1"
IRD_FORM_VERSION = "0001"
PAY_CYCLE_CODES = {
    "weekly": "WK",
    "fortnightly": "FT",
    "monthly": "MT",
}


def _money_to_cents(value) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return str(int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def _date(value) -> str:
    return value.strftime("%Y%m%d") if value else ""


def _contact_field(value: str | None) -> str:
    return str(value or "").replace(",", " ").strip()


def _employee_name(stub) -> str:
    return f"{stub.employee.first_name} {stub.employee.last_name}".strip()


def _employee_start_date(stub, pay_run: PayRun) -> str:
    start_date = stub.employee.start_date
    if start_date and pay_run.period_start <= start_date <= pay_run.period_end:
        return _date(start_date)
    return ""


def _employee_end_date(stub, pay_run: PayRun) -> str:
    end_date = stub.employee.end_date
    if end_date and pay_run.period_start <= end_date <= pay_run.period_end:
        return _date(end_date)
    return ""


def _net_employer_kiwisaver(stub) -> Decimal:
    return Decimal(str(stub.employer_kiwisaver_contribution or 0)) - Decimal(str(stub.esct or 0))


def _header_contact_name(settings: dict) -> str:
    return _contact_field(settings.get("payroll_contact_name") or settings.get("company_name"))


def _header_contact_phone(settings: dict) -> str:
    return _contact_field(settings.get("payroll_contact_phone") or settings.get("company_phone"))


def _header_contact_email(settings: dict) -> str:
    return _contact_field(settings.get("payroll_contact_email") or settings.get("company_email"))


def validate_employment_information_export(pay_run: PayRun, settings: dict) -> None:
    if str(pay_run.status.value if hasattr(pay_run.status, "value") else pay_run.status).lower() != "processed":
        raise ValueError("Employment Information export is only available for processed pay runs")
    if not str(settings.get("ird_number") or "").strip():
        raise ValueError("IRD number is required before exporting Employment Information")
    if not _header_contact_phone(settings):
        raise ValueError("Payroll contact phone is required before exporting Employment Information")
    if not _header_contact_email(settings):
        raise ValueError("Payroll contact email is required before exporting Employment Information")
    for stub in pay_run.stubs:
        frequency = str(stub.employee.pay_frequency or "").lower()
        if frequency not in PAY_CYCLE_CODES:
            raise ValueError(f"Unsupported pay frequency for Employment Information export: {frequency}")


def generate_employment_information_csv(pay_run: PayRun, settings: dict) -> str:
    validate_employment_information_export(pay_run, settings)

    stubs = list(pay_run.stubs)
    total_gross = sum((Decimal(str(stub.gross_pay or 0)) for stub in stubs), Decimal("0.00"))
    total_paye = sum((Decimal(str(stub.paye or 0)) for stub in stubs), Decimal("0.00"))
    total_child_support = sum((Decimal(str(stub.child_support_deduction or 0)) for stub in stubs), Decimal("0.00"))
    total_student_loan = sum((Decimal(str(stub.student_loan_deduction or 0)) for stub in stubs), Decimal("0.00"))
    total_kiwisaver = sum((Decimal(str(stub.kiwisaver_employee_deduction or 0)) for stub in stubs), Decimal("0.00"))
    total_net_employer_kiwisaver = sum((_net_employer_kiwisaver(stub) for stub in stubs), Decimal("0.00"))
    total_esct = sum((Decimal(str(stub.esct or 0)) for stub in stubs), Decimal("0.00"))
    total_amounts_deducted = (
        total_paye
        + total_child_support
        + total_student_loan
        + total_kiwisaver
        + total_net_employer_kiwisaver
        + total_esct
    )

    out = StringIO()
    writer = csv.writer(out, lineterminator="\n")

    writer.writerow([
        "HEI2",
        str(settings.get("ird_number") or "").strip(),
        _date(pay_run.pay_date),
        "N",
        "N",
        "",
        _header_contact_name(settings),
        _header_contact_phone(settings),
        _header_contact_email(settings),
        len(stubs),
        _money_to_cents(total_gross),
        _money_to_cents(Decimal("0.00")),
        _money_to_cents(Decimal("0.00")),
        _money_to_cents(total_paye),
        _money_to_cents(Decimal("0.00")),
        _money_to_cents(total_child_support),
        _money_to_cents(total_student_loan),
        _money_to_cents(Decimal("0.00")),
        _money_to_cents(Decimal("0.00")),
        _money_to_cents(total_kiwisaver),
        _money_to_cents(total_net_employer_kiwisaver),
        _money_to_cents(total_esct),
        _money_to_cents(total_amounts_deducted),
        _money_to_cents(Decimal("0.00")),
        _money_to_cents(Decimal("0.00")),
        _money_to_cents(Decimal("0.00")),
        PACKAGE_VERSION_IDENTIFIER,
        IRD_FORM_VERSION,
    ])

    for stub in stubs:
        writer.writerow([
            "DEI",
            (str(stub.employee.ird_number or "").strip() or "000000000"),
            _employee_name(stub),
            stub.tax_code,
            _employee_start_date(stub, pay_run),
            _employee_end_date(stub, pay_run),
            _date(pay_run.period_start),
            _date(pay_run.period_end),
            PAY_CYCLE_CODES[str(stub.employee.pay_frequency).lower()],
            _money_to_cents(stub.hours or 0),
            _money_to_cents(stub.gross_pay or 0),
            _money_to_cents(Decimal("0.00")),
            _money_to_cents(Decimal("0.00")),
            "0",
            _money_to_cents(stub.paye or 0),
            _money_to_cents(Decimal("0.00")),
            _money_to_cents(stub.child_support_deduction or 0),
            "",
            _money_to_cents(stub.student_loan_deduction or 0),
            _money_to_cents(Decimal("0.00")),
            _money_to_cents(Decimal("0.00")),
            _money_to_cents(stub.kiwisaver_employee_deduction or 0),
            _money_to_cents(_net_employer_kiwisaver(stub)),
            _money_to_cents(stub.esct or 0),
            _money_to_cents(Decimal("0.00")),
            _money_to_cents(Decimal("0.00")),
            _money_to_cents(Decimal("0.00")),
        ])

    return out.getvalue()

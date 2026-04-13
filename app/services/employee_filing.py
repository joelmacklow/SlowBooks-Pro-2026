import csv
from io import StringIO


def _date(value) -> str:
    return value.strftime("%Y%m%d") if value else ""


def _clean(value: str | None) -> str:
    return str(value or "").replace(",", " ").strip()


def _employee_name(employee) -> str:
    return f"{employee.first_name} {employee.last_name}".strip()


def validate_employee_filing(employee, filing_type: str, settings: dict) -> None:
    if not str(settings.get("ird_number") or "").strip():
        raise ValueError("IRD number is required before exporting employee filing")
    if not str(employee.ird_number or "").strip():
        raise ValueError("Employee IRD number is required before exporting employee filing")
    if filing_type == "starter" and not employee.start_date:
        raise ValueError("Employee start date is required for starter filing")
    if filing_type == "leaver" and not employee.end_date:
        raise ValueError("Employee end date is required for leaver filing")


def generate_employee_filing_csv(employee, filing_type: str, settings: dict) -> str:
    validate_employee_filing(employee, filing_type, settings)

    out = StringIO()
    writer = csv.writer(out, lineterminator="\n")
    record = "SED" if filing_type == "starter" else "LED"
    filing_date = employee.start_date if filing_type == "starter" else employee.end_date

    writer.writerow([
        record,
        _clean(settings.get("ird_number")),
        _clean(employee.ird_number),
        _employee_name(employee),
        _date(filing_date),
        _clean(employee.tax_code),
        _clean(employee.pay_frequency),
        "Y" if employee.kiwisaver_enrolled else "N",
    ])

    return out.getvalue()

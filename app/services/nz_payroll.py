from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from app.models.payroll import Employee


MONEY = Decimal("0.01")
RATE = Decimal("0.0001")
WHOLE_DOLLAR = Decimal("1")
STUDENT_LOAN_RATE = Decimal("0.12")


def round_money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)


def truncate_cents(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_DOWN)


def truncate_dollars(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(WHOLE_DOLLAR, rounding=ROUND_DOWN)


@dataclass(frozen=True)
class PayrollTaxYearRules:
    tax_year: int
    start_date: date
    end_date: date
    acc_rate: Decimal
    acc_max_earnings: Decimal
    student_loan_annual_threshold: Decimal
    employer_kiwisaver_rate: Decimal
    income_brackets: tuple[tuple[Decimal, Decimal, Decimal], ...]
    ietc_lower_threshold: Decimal
    ietc_flat_max_threshold: Decimal
    ietc_upper_threshold: Decimal
    ietc_amount: Decimal
    ietc_abatement_rate: Decimal


PAYROLL_RULES = (
    PayrollTaxYearRules(
        tax_year=2026,
        start_date=date(2025, 4, 1),
        end_date=date(2026, 3, 31),
        acc_rate=Decimal("0.0167"),
        acc_max_earnings=Decimal("152790"),
        student_loan_annual_threshold=Decimal("24128"),
        employer_kiwisaver_rate=Decimal("0.0300"),
        income_brackets=(
            (Decimal("15600"), Decimal("0.105"), Decimal("0.00")),
            (Decimal("53500"), Decimal("0.175"), Decimal("1092.00")),
            (Decimal("78100"), Decimal("0.30"), Decimal("7779.50")),
            (Decimal("180000"), Decimal("0.33"), Decimal("10122.50")),
            (Decimal("999999999"), Decimal("0.39"), Decimal("20922.50")),
        ),
        ietc_lower_threshold=Decimal("24000"),
        ietc_flat_max_threshold=Decimal("66000"),
        ietc_upper_threshold=Decimal("70000"),
        ietc_amount=Decimal("520.00"),
        ietc_abatement_rate=Decimal("0.13"),
    ),
    PayrollTaxYearRules(
        tax_year=2027,
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        acc_rate=Decimal("0.0175"),
        acc_max_earnings=Decimal("156641"),
        student_loan_annual_threshold=Decimal("24128"),
        employer_kiwisaver_rate=Decimal("0.0350"),
        income_brackets=(
            (Decimal("15600"), Decimal("0.105"), Decimal("0.00")),
            (Decimal("53500"), Decimal("0.175"), Decimal("1092.00")),
            (Decimal("78100"), Decimal("0.30"), Decimal("7779.50")),
            (Decimal("180000"), Decimal("0.33"), Decimal("10122.50")),
            (Decimal("999999999"), Decimal("0.39"), Decimal("20922.50")),
        ),
        ietc_lower_threshold=Decimal("24000"),
        ietc_flat_max_threshold=Decimal("66000"),
        ietc_upper_threshold=Decimal("70000"),
        ietc_amount=Decimal("520.00"),
        ietc_abatement_rate=Decimal("0.13"),
    ),
)

PAYS_PER_YEAR = {
    "weekly": Decimal("52"),
    "fortnightly": Decimal("26"),
    "monthly": Decimal("12"),
}

SECONDARY_RATES = {
    "SB": Decimal("0.105"),
    "S": Decimal("0.175"),
    "SH": Decimal("0.30"),
    "ST": Decimal("0.33"),
    "SA": Decimal("0.39"),
}


def normalize_tax_code(value: str | None) -> str:
    return " ".join(str(value or "M").upper().split())


def resolve_tax_year_rules(pay_date: date) -> PayrollTaxYearRules:
    for rules in PAYROLL_RULES:
        if rules.start_date <= pay_date <= rules.end_date:
            return rules
    raise ValueError(f"No NZ payroll rules configured for pay date {pay_date.isoformat()}")


def employer_kiwisaver_rate(rules: PayrollTaxYearRules) -> Decimal:
    return rules.employer_kiwisaver_rate


def pays_per_year(pay_frequency: str) -> Decimal:
    frequency = str(pay_frequency).lower()
    if frequency not in PAYS_PER_YEAR:
        raise ValueError(f"Unsupported pay frequency {pay_frequency}")
    return PAYS_PER_YEAR[frequency]


def period_threshold(rules: PayrollTaxYearRules, pay_frequency: str) -> Decimal:
    return rules.student_loan_annual_threshold / pays_per_year(pay_frequency)


def calculate_annual_income_tax(annual_income: Decimal, rules: PayrollTaxYearRules) -> Decimal:
    for ceiling, rate, offset in rules.income_brackets:
        if annual_income <= ceiling:
            return (annual_income * rate) - offset
    return Decimal("0.00")


def calculate_ietc(annual_income: Decimal, rules: PayrollTaxYearRules) -> Decimal:
    if annual_income < rules.ietc_lower_threshold:
        return Decimal("0.00")
    if annual_income <= rules.ietc_flat_max_threshold:
        return rules.ietc_amount
    if annual_income >= rules.ietc_upper_threshold:
        return Decimal("0.00")
    return rules.ietc_amount - ((annual_income - rules.ietc_flat_max_threshold) * rules.ietc_abatement_rate)


def calculate_annual_acc(annual_income: Decimal, rules: PayrollTaxYearRules) -> Decimal:
    capped_income = min(annual_income, rules.acc_max_earnings)
    return capped_income * rules.acc_rate


def calculate_period_gross(employee: Employee, hours: Decimal = Decimal("0")) -> Decimal:
    if employee.pay_type.value == "salary":
        return round_money(Decimal(str(employee.pay_rate)) / pays_per_year(employee.pay_frequency))
    return round_money(Decimal(str(employee.pay_rate)) * Decimal(str(hours or 0)))


def derive_esct_rate(employee: Employee, annual_income: Decimal, rules: PayrollTaxYearRules) -> Decimal:
    configured = Decimal(str(employee.esct_rate or 0)).quantize(RATE)
    if configured > 0:
        return configured
    estimated_annual_contribution = annual_income * employer_kiwisaver_rate(rules)
    threshold_amount = annual_income + estimated_annual_contribution
    if threshold_amount <= Decimal("18720"):
        return Decimal("0.1050")
    if threshold_amount <= Decimal("64200"):
        return Decimal("0.1750")
    if threshold_amount <= Decimal("93720"):
        return Decimal("0.3000")
    if threshold_amount <= Decimal("216000"):
        return Decimal("0.3300")
    return Decimal("0.3900")


@dataclass(frozen=True)
class PayrollStubResult:
    tax_year: int
    tax_code: str
    hours: Decimal
    gross_pay: Decimal
    paye: Decimal
    acc_earners_levy: Decimal
    student_loan_deduction: Decimal
    kiwisaver_employee_deduction: Decimal
    employer_kiwisaver_contribution: Decimal
    employer_kiwisaver_net: Decimal
    esct: Decimal
    child_support_deduction: Decimal
    total_deductions: Decimal
    net_pay: Decimal


def _primary_code_parts(pay_amount: Decimal, employee: Employee, rules: PayrollTaxYearRules, tax_code: str) -> tuple[Decimal, Decimal]:
    annual_income = truncate_dollars(pay_amount * pays_per_year(employee.pay_frequency))
    annual_tax = calculate_annual_income_tax(annual_income, rules)
    if tax_code.startswith("ME"):
        annual_tax -= calculate_ietc(annual_income, rules)
    annual_acc = calculate_annual_acc(annual_income, rules)

    weekly_tax = truncate_cents(annual_tax / Decimal("52"))
    weekly_acc = truncate_cents(annual_acc / Decimal("52"))
    paye = truncate_cents((weekly_tax * Decimal("52")) / pays_per_year(employee.pay_frequency))
    acc = truncate_cents((weekly_acc * Decimal("52")) / pays_per_year(employee.pay_frequency))
    return paye, acc


def _secondary_code_parts(pay_amount: Decimal, rules: PayrollTaxYearRules, tax_code: str) -> tuple[Decimal, Decimal]:
    base_code = tax_code.replace(" SL", "")
    if base_code not in SECONDARY_RATES:
        raise ValueError(f"Unsupported NZ tax code {tax_code}")
    pay_period_amount = truncate_dollars(pay_amount)
    paye = truncate_cents(pay_period_amount * SECONDARY_RATES[base_code])
    acc = truncate_cents(pay_period_amount * rules.acc_rate)
    return paye, acc


def _nd_code_parts(pay_amount: Decimal, rules: PayrollTaxYearRules) -> tuple[Decimal, Decimal]:
    pay_period_amount = truncate_dollars(pay_amount)
    return truncate_cents(pay_period_amount * Decimal("0.45")), truncate_cents(pay_period_amount * rules.acc_rate)


def _nsw_code_parts(pay_amount: Decimal, rules: PayrollTaxYearRules) -> tuple[Decimal, Decimal]:
    pay_period_amount = truncate_dollars(pay_amount)
    return truncate_cents(pay_period_amount * Decimal("0.105")), truncate_cents(pay_period_amount * rules.acc_rate)


def calculate_student_loan(pay_amount: Decimal, pay_frequency: str, tax_code: str, rules: PayrollTaxYearRules) -> Decimal:
    normalized = normalize_tax_code(tax_code)
    pay_period_amount = truncate_dollars(pay_amount)
    if normalized in {"M SL", "ME SL"}:
        threshold = period_threshold(rules, pay_frequency)
        if pay_period_amount <= threshold:
            return Decimal("0.00")
        return truncate_cents((pay_period_amount - threshold) * STUDENT_LOAN_RATE)
    if normalized.endswith(" SL") and normalized.replace(" SL", "") in SECONDARY_RATES:
        return truncate_cents(pay_period_amount * STUDENT_LOAN_RATE)
    return Decimal("0.00")


def calculate_child_support(employee: Employee, gross_pay: Decimal, paye: Decimal) -> Decimal:
    if not employee.child_support:
        return Decimal("0.00")
    notice_amount = Decimal(str(getattr(employee, "child_support_amount", 0) or 0))
    if notice_amount <= 0:
        return Decimal("0.00")
    protected_net_earnings = (gross_pay - paye) * Decimal("0.60")
    maximum_deduction = gross_pay - paye - protected_net_earnings
    if maximum_deduction <= 0:
        return Decimal("0.00")
    return truncate_cents(min(notice_amount, maximum_deduction))


def calculate_payroll_stub(employee: Employee, pay_date: date, hours: Decimal = Decimal("0")) -> PayrollStubResult:
    rules = resolve_tax_year_rules(pay_date)
    tax_code = normalize_tax_code(employee.tax_code)
    gross_pay = calculate_period_gross(employee, hours)

    if tax_code in {"M", "ME", "M SL", "ME SL"}:
        paye, acc = _primary_code_parts(gross_pay, employee, rules, tax_code)
    elif tax_code.replace(" SL", "") in SECONDARY_RATES:
        paye, acc = _secondary_code_parts(gross_pay, rules, tax_code)
    elif tax_code == "ND":
        paye, acc = _nd_code_parts(gross_pay, rules)
    elif tax_code == "NSW":
        paye, acc = _nsw_code_parts(gross_pay, rules)
    else:
        raise ValueError(f"Unsupported NZ tax code {tax_code}")

    student_loan = calculate_student_loan(gross_pay, employee.pay_frequency, tax_code, rules)
    child_support = calculate_child_support(employee, gross_pay, paye)

    kiwisaver_employee = Decimal("0.00")
    employer_kiwisaver = Decimal("0.00")
    employer_kiwisaver_net = Decimal("0.00")
    esct = Decimal("0.00")
    if employee.kiwisaver_enrolled and tax_code != "NSW":
        employee_rate = Decimal(str(employee.kiwisaver_rate or 0)).quantize(RATE)
        if employee_rate > 0:
            kiwisaver_employee = round_money(gross_pay * employee_rate)
        employer_kiwisaver = round_money(gross_pay * employer_kiwisaver_rate(rules))
        esct_rate = derive_esct_rate(employee, truncate_dollars(gross_pay * pays_per_year(employee.pay_frequency)), rules)
        esct = truncate_cents(employer_kiwisaver * esct_rate)
        employer_kiwisaver_net = employer_kiwisaver - esct

    total_deductions = round_money(paye + acc + student_loan + kiwisaver_employee + child_support)
    net_pay = round_money(gross_pay - total_deductions)

    return PayrollStubResult(
        tax_year=rules.tax_year,
        tax_code=tax_code,
        hours=round_money(hours),
        gross_pay=gross_pay,
        paye=paye,
        acc_earners_levy=acc,
        student_loan_deduction=student_loan,
        kiwisaver_employee_deduction=kiwisaver_employee,
        employer_kiwisaver_contribution=employer_kiwisaver,
        employer_kiwisaver_net=employer_kiwisaver_net,
        esct=esct,
        child_support_deduction=child_support,
        total_deductions=total_deductions,
        net_pay=net_pay,
    )

# ============================================================================
# Payroll Service — withholding calculations
# Feature 17: Simplified flat-rate or IRS percentage method
# SS 6.2%, Medicare 1.45%. Simplified federal/state withholding.
# DISCLAIMER: Users should verify with tax professional.
# ============================================================================

from decimal import Decimal

# Tax rates (simplified 2026)
SS_RATE = Decimal("0.062")       # Social Security 6.2%
SS_WAGE_BASE = Decimal("168600")  # 2026 SS wage base (approximate)
MEDICARE_RATE = Decimal("0.0145")  # Medicare 1.45%

# Simplified federal withholding brackets (2026 approximate, single)
FEDERAL_BRACKETS_SINGLE = [
    (Decimal("11600"), Decimal("0.10")),
    (Decimal("47150"), Decimal("0.12")),
    (Decimal("100525"), Decimal("0.22")),
    (Decimal("191950"), Decimal("0.24")),
    (Decimal("243725"), Decimal("0.32")),
    (Decimal("609350"), Decimal("0.35")),
    (Decimal("999999999"), Decimal("0.37")),
]

# State tax: simplified flat rate (user's state may vary)
STATE_TAX_RATE = Decimal("0.05")  # 5% flat approximation


def calculate_withholdings(gross_pay: Decimal, pay_periods: int = 26,
                           filing_status: str = "single",
                           allowances: int = 0) -> dict:
    """Calculate federal, state, SS, and Medicare withholdings.

    gross_pay: gross pay for this pay period
    pay_periods: number of pay periods per year (26 = biweekly, 52 = weekly, 24 = semi-monthly)
    """
    if gross_pay <= 0:
        return {"federal": Decimal("0"), "state": Decimal("0"),
                "ss": Decimal("0"), "medicare": Decimal("0"), "total": Decimal("0")}

    # Annualize
    annual_gross = gross_pay * pay_periods

    # Federal withholding (simplified progressive brackets)
    federal_annual = Decimal("0")
    remaining = annual_gross - (Decimal("4300") * allowances)  # Allowance deduction
    if remaining < 0:
        remaining = Decimal("0")

    prev_bracket = Decimal("0")
    for bracket_top, rate in FEDERAL_BRACKETS_SINGLE:
        taxable = min(remaining, bracket_top) - prev_bracket
        if taxable > 0:
            federal_annual += taxable * rate
        prev_bracket = bracket_top
        if remaining <= bracket_top:
            break

    federal = (federal_annual / pay_periods).quantize(Decimal("0.01"))

    # State (flat rate)
    state = (gross_pay * STATE_TAX_RATE).quantize(Decimal("0.01"))

    # Social Security
    ss = (gross_pay * SS_RATE).quantize(Decimal("0.01"))

    # Medicare
    medicare = (gross_pay * MEDICARE_RATE).quantize(Decimal("0.01"))

    total = federal + state + ss + medicare

    return {
        "federal": federal,
        "state": state,
        "ss": ss,
        "medicare": medicare,
        "total": total,
    }

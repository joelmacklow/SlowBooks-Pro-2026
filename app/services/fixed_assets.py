from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.accounts import Account, AccountType
from app.models.fixed_assets import (
    FixedAsset,
    FixedAssetAcquisitionMethod,
    FixedAssetAveragingMethod,
    FixedAssetCalculationBasis,
    FixedAssetDepreciationMethod,
    FixedAssetStatus,
    FixedAssetType,
)
from app.models.settings import DEFAULT_SETTINGS, Settings
from app.services.accounting import (
    create_journal_entry,
    get_default_expense_account_id,
    get_default_income_account_id,
    get_fixed_asset_accumulated_depreciation_account_id,
    get_fixed_asset_depreciation_expense_account_id,
    reverse_journal_entry,
)

TEMPLATE_HEADERS = [
    "*AssetName", "*AssetNumber", "AssetStatus", "PurchaseDate", "PurchasePrice", "AssetType", "Description",
    "TrackingCategory1", "TrackingOption1", "TrackingCategory2", "TrackingOption2", "SerialNumber", "WarrantyExpiry",
    "Book_DepreciationStartDate", "Book_CostLimit", "Book_ResidualValue", "Book_DepreciationMethod",
    "Book_AveragingMethod", "Book_Rate", "Book_EffectiveLife", "Book_OpeningBookAccumulatedDepreciation",
    "Book_BookValue", "AccumulatedDepreciation", "InvestmentBoost", "DepreciationToDate", "DisposalDate",
]


@dataclass(frozen=True)
class DepreciationComputation:
    amount: Decimal
    annual_amount: Decimal
    rate: Decimal
    months: int


def _money(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate_value(value) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _effective_life(value) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_date(value) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%-d %b %Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {text}") from exc


def _settings_map(db: Session) -> dict:
    settings = dict(DEFAULT_SETTINGS)
    for row in db.query(Settings).all():
        settings[row.key] = row.value
    return settings


def financial_year_window(db: Session, end_date: date) -> tuple[date, date]:
    settings = _settings_map(db)
    start_value = str(settings.get("financial_year_start") or "").strip()
    if start_value:
        month, day = [int(part) for part in start_value.split("-")]
    else:
        month, day = 1, 1
    candidate = date(end_date.year, month, day)
    start_date = candidate if end_date >= candidate else date(end_date.year - 1, month, day)
    return start_date, end_date


def current_book_value(asset: FixedAsset) -> Decimal:
    return max(
        Decimal("0.00"),
        _money(asset.purchase_price) - _money(asset.opening_accumulated_depreciation) - _money(asset.accumulated_depreciation),
    )


def total_accumulated_depreciation(asset: FixedAsset) -> Decimal:
    return _money(asset.opening_accumulated_depreciation) + _money(asset.accumulated_depreciation)


def _next_asset_number(db: Session) -> str:
    existing = db.query(FixedAsset.asset_number).order_by(FixedAsset.asset_number.desc()).all()
    max_number = 0
    for (value,) in existing:
        if isinstance(value, str) and value.startswith("FA-"):
            suffix = value[3:]
            if suffix.isdigit():
                max_number = max(max_number, int(suffix))
    return f"FA-{max_number + 1:04d}"


def _active_account(db: Session, account_id: int | None, *, expected_type: AccountType | None = None, required: bool = False) -> Account | None:
    if not account_id:
        if required:
            raise HTTPException(status_code=400, detail="Account is required")
        return None
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.is_active:
        raise HTTPException(status_code=400, detail="Account must be active")
    if expected_type and account.account_type != expected_type:
        raise HTTPException(status_code=400, detail=f"Account must be of type {expected_type.value}")
    return account


def _asset_type_defaults(db: Session) -> tuple[int | None, int | None]:
    return (
        get_fixed_asset_accumulated_depreciation_account_id(db, allow_create=False),
        get_fixed_asset_depreciation_expense_account_id(db, allow_create=False),
    )


def list_asset_types_payload(db: Session) -> list[dict]:
    rows = db.query(FixedAssetType).order_by(FixedAssetType.name).all()
    return [asset_type_payload(db, row) for row in rows]


def asset_type_payload(db: Session, row: FixedAssetType) -> dict:
    default_acc_dep_id, default_dep_exp_id = _asset_type_defaults(db)
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "asset_account_id": row.asset_account_id,
        "accumulated_depreciation_account_id": row.accumulated_depreciation_account_id,
        "depreciation_expense_account_id": row.depreciation_expense_account_id,
        "default_depreciation_method": row.default_depreciation_method.value,
        "default_calculation_basis": row.default_calculation_basis.value,
        "default_rate": float(row.default_rate) if row.default_rate is not None else None,
        "default_effective_life_years": float(row.default_effective_life_years) if row.default_effective_life_years is not None else None,
        "default_cost_limit": float(row.default_cost_limit) if row.default_cost_limit is not None else None,
        "is_active": bool(row.is_active),
        "asset_account": _account_payload(row.asset_account),
        "accumulated_depreciation_account": _account_payload(row.accumulated_depreciation_account),
        "depreciation_expense_account": _account_payload(row.depreciation_expense_account),
        "default_accumulated_depreciation_account_id": default_acc_dep_id,
        "default_depreciation_expense_account_id": default_dep_exp_id,
    }


def _account_payload(account: Account | None) -> dict | None:
    if not account:
        return None
    return {
        "id": account.id,
        "account_number": account.account_number,
        "name": account.name,
        "account_type": account.account_type.value,
    }


def create_asset_type(db: Session, data: dict) -> dict:
    _active_account(db, data.get("asset_account_id"), expected_type=AccountType.ASSET)
    _active_account(db, data.get("accumulated_depreciation_account_id"), expected_type=AccountType.ASSET)
    _active_account(db, data.get("depreciation_expense_account_id"), expected_type=AccountType.EXPENSE)
    row = FixedAssetType(
        name=str(data["name"]).strip(),
        description=(data.get("description") or "").strip() or None,
        asset_account_id=data.get("asset_account_id"),
        accumulated_depreciation_account_id=data.get("accumulated_depreciation_account_id"),
        depreciation_expense_account_id=data.get("depreciation_expense_account_id"),
        default_depreciation_method=FixedAssetDepreciationMethod(data.get("default_depreciation_method") or "dv"),
        default_calculation_basis=FixedAssetCalculationBasis(data.get("default_calculation_basis") or "rate"),
        default_rate=_rate_value(data.get("default_rate")),
        default_effective_life_years=_effective_life(data.get("default_effective_life_years")),
        default_cost_limit=_money(data.get("default_cost_limit")) if data.get("default_cost_limit") not in (None, "") else None,
        is_active=bool(data.get("is_active", True)),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return asset_type_payload(db, row)


def update_asset_type(db: Session, asset_type_id: int, data: dict) -> dict:
    row = db.query(FixedAssetType).filter(FixedAssetType.id == asset_type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Asset type not found")
    if "asset_account_id" in data:
        _active_account(db, data.get("asset_account_id"), expected_type=AccountType.ASSET)
        row.asset_account_id = data.get("asset_account_id")
    if "accumulated_depreciation_account_id" in data:
        _active_account(db, data.get("accumulated_depreciation_account_id"), expected_type=AccountType.ASSET)
        row.accumulated_depreciation_account_id = data.get("accumulated_depreciation_account_id")
    if "depreciation_expense_account_id" in data:
        _active_account(db, data.get("depreciation_expense_account_id"), expected_type=AccountType.EXPENSE)
        row.depreciation_expense_account_id = data.get("depreciation_expense_account_id")
    for field in ("name", "description", "is_active"):
        if field in data:
            value = data[field]
            setattr(row, field, (str(value).strip() if isinstance(value, str) else value))
    if "default_depreciation_method" in data:
        row.default_depreciation_method = FixedAssetDepreciationMethod(data["default_depreciation_method"])
    if "default_calculation_basis" in data:
        row.default_calculation_basis = FixedAssetCalculationBasis(data["default_calculation_basis"])
    if "default_rate" in data:
        row.default_rate = _rate_value(data.get("default_rate"))
    if "default_effective_life_years" in data:
        row.default_effective_life_years = _effective_life(data.get("default_effective_life_years"))
    if "default_cost_limit" in data:
        row.default_cost_limit = _money(data.get("default_cost_limit")) if data.get("default_cost_limit") not in (None, "") else None
    db.commit()
    db.refresh(row)
    return asset_type_payload(db, row)


def _asset_type_or_404(db: Session, asset_type_id: int) -> FixedAssetType:
    row = db.query(FixedAssetType).filter(FixedAssetType.id == asset_type_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Asset type not found")
    return row


def _populate_asset_from_data(asset: FixedAsset, asset_type: FixedAssetType, data: dict) -> None:
    asset.name = str(data["name"]).strip()
    asset.asset_type_id = asset_type.id
    asset.purchase_date = _parse_date(data.get("purchase_date")) or asset.purchase_date
    asset.purchase_price = _money(data.get("purchase_price"))
    asset.description = (data.get("description") or "").strip() or None
    asset.serial_number = (data.get("serial_number") or "").strip() or None
    asset.warranty_expiry = _parse_date(data.get("warranty_expiry"))
    asset.depreciation_start_date = _parse_date(data.get("depreciation_start_date")) or asset.purchase_date
    asset.cost_limit = _money(data.get("cost_limit")) if data.get("cost_limit") not in (None, "") else None
    asset.residual_value = _money(data.get("residual_value"))
    asset.depreciation_method = FixedAssetDepreciationMethod(data.get("depreciation_method") or asset_type.default_depreciation_method.value)
    asset.calculation_basis = FixedAssetCalculationBasis(data.get("calculation_basis") or asset_type.default_calculation_basis.value)
    asset.averaging_method = FixedAssetAveragingMethod(data.get("averaging_method") or "full_month")
    asset.rate = _rate_value(data.get("rate")) if data.get("rate") not in (None, "") else asset_type.default_rate
    asset.effective_life_years = _effective_life(data.get("effective_life_years")) if data.get("effective_life_years") not in (None, "") else asset_type.default_effective_life_years
    asset.opening_accumulated_depreciation = _money(data.get("opening_accumulated_depreciation"))
    asset.investment_boost = _money(data.get("investment_boost")) if data.get("investment_boost") not in (None, "") else None
    asset.acquisition_method = FixedAssetAcquisitionMethod(data.get("acquisition_method") or "cash")
    asset.offset_account_id = data.get("offset_account_id")
    asset.source_reference = (data.get("source_reference") or "").strip() or None


def _create_acquisition_journal(db: Session, asset: FixedAsset, asset_type: FixedAssetType) -> int | None:
    if asset.acquisition_method in {FixedAssetAcquisitionMethod.OPENING_BALANCE, FixedAssetAcquisitionMethod.IMPORT_CSV}:
        return None
    asset_account = _active_account(db, asset_type.asset_account_id, expected_type=AccountType.ASSET, required=True)
    offset_account = _active_account(db, asset.offset_account_id, required=True)
    txn = create_journal_entry(
        db,
        asset.purchase_date,
        f"Fixed asset acquisition - {asset.asset_number}",
        [
            {"account_id": asset_account.id, "debit": asset.purchase_price, "credit": Decimal("0.00"), "description": asset.name},
            {"account_id": offset_account.id, "debit": Decimal("0.00"), "credit": asset.purchase_price, "description": asset.name},
        ],
        source_type="fixed_asset_acquisition",
        source_id=asset.id,
        reference=asset.asset_number,
    )
    db.flush()
    return txn.id


def create_asset(db: Session, data: dict) -> dict:
    asset_type = _asset_type_or_404(db, int(data["asset_type_id"]))
    asset = FixedAsset(
        asset_number=(str(data.get("asset_number") or "").strip() or _next_asset_number(db)),
        status=FixedAssetStatus.REGISTERED,
    )
    _populate_asset_from_data(asset, asset_type, data)
    db.add(asset)
    db.flush()
    asset.acquisition_transaction_id = _create_acquisition_journal(db, asset, asset_type)
    db.commit()
    db.refresh(asset)
    return asset_payload(db, asset)


def update_asset(db: Session, asset_id: int, data: dict) -> dict:
    asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    asset_type = _asset_type_or_404(db, int(data.get("asset_type_id") or asset.asset_type_id))
    restricted_fields = {"asset_type_id", "purchase_date", "purchase_price", "offset_account_id", "acquisition_method"}
    if asset.acquisition_transaction_id and any(field in data for field in restricted_fields):
        raise HTTPException(status_code=400, detail="Accounting-linked fields cannot be changed after registration")
    merged = {
        "name": data.get("name", asset.name),
        "purchase_date": data.get("purchase_date", asset.purchase_date),
        "purchase_price": data.get("purchase_price", asset.purchase_price),
        "description": data.get("description", asset.description),
        "serial_number": data.get("serial_number", asset.serial_number),
        "warranty_expiry": data.get("warranty_expiry", asset.warranty_expiry),
        "depreciation_start_date": data.get("depreciation_start_date", asset.depreciation_start_date),
        "cost_limit": data.get("cost_limit", asset.cost_limit),
        "residual_value": data.get("residual_value", asset.residual_value),
        "depreciation_method": data.get("depreciation_method", asset.depreciation_method.value),
        "calculation_basis": data.get("calculation_basis", asset.calculation_basis.value),
        "averaging_method": data.get("averaging_method", asset.averaging_method.value),
        "rate": data.get("rate", asset.rate),
        "effective_life_years": data.get("effective_life_years", asset.effective_life_years),
        "opening_accumulated_depreciation": data.get("opening_accumulated_depreciation", asset.opening_accumulated_depreciation),
        "investment_boost": data.get("investment_boost", asset.investment_boost),
        "asset_type_id": asset_type.id,
        "acquisition_method": data.get("acquisition_method", asset.acquisition_method.value),
        "offset_account_id": data.get("offset_account_id", asset.offset_account_id),
        "source_reference": data.get("source_reference", asset.source_reference),
    }
    _populate_asset_from_data(asset, asset_type, merged)
    db.commit()
    db.refresh(asset)
    return asset_payload(db, asset)


def _derived_rate(asset: FixedAsset) -> Decimal:
    if asset.rate not in (None, ""):
        return _rate_value(asset.rate) or Decimal("0.0000")
    life = _effective_life(asset.effective_life_years)
    if not life or life <= 0:
        return Decimal("0.0000")
    if asset.depreciation_method == FixedAssetDepreciationMethod.DIMINISHING_VALUE:
        return (Decimal("200") / life).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return (Decimal("100") / life).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _full_month_count(start_date: date, end_date: date) -> int:
    if start_date > end_date:
        return 0
    return ((end_date.year - start_date.year) * 12) + (end_date.month - start_date.month) + 1


def compute_period_depreciation(asset: FixedAsset, fy_start: date, run_date: date) -> DepreciationComputation:
    if asset.status != FixedAssetStatus.REGISTERED:
        return DepreciationComputation(amount=Decimal("0.00"), annual_amount=Decimal("0.00"), rate=Decimal("0.0000"), months=0)
    start_date = max(asset.depreciation_start_date, fy_start)
    if asset.last_depreciation_run_date:
        next_date = asset.last_depreciation_run_date.replace(day=asset.last_depreciation_run_date.day)
        if next_date >= start_date:
            start_date = next_date.replace(day=1)
            start_date = date(start_date.year + (1 if start_date.month == 12 else 0), 1 if start_date.month == 12 else start_date.month + 1, 1)
    if asset.disposal_date and asset.disposal_date <= run_date:
        run_date = asset.disposal_date
    if start_date > run_date:
        return DepreciationComputation(amount=Decimal("0.00"), annual_amount=Decimal("0.00"), rate=Decimal("0.0000"), months=0)

    book_before = current_book_value(asset)
    if book_before <= 0:
        return DepreciationComputation(amount=Decimal("0.00"), annual_amount=Decimal("0.00"), rate=Decimal("0.0000"), months=0)

    rate = _derived_rate(asset)
    if rate <= 0:
        return DepreciationComputation(amount=Decimal("0.00"), annual_amount=Decimal("0.00"), rate=rate, months=0)
    months = _full_month_count(start_date, run_date)
    if months <= 0:
        return DepreciationComputation(amount=Decimal("0.00"), annual_amount=Decimal("0.00"), rate=rate, months=0)

    residual = _money(asset.residual_value)
    if asset.depreciation_method == FixedAssetDepreciationMethod.STRAIGHT_LINE:
        if asset.calculation_basis == FixedAssetCalculationBasis.EFFECTIVE_LIFE and asset.effective_life_years not in (None, ""):
            annual = ((_money(asset.purchase_price) - residual) / _effective_life(asset.effective_life_years)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            annual = (_money(asset.purchase_price) * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        annual = ((book_before - residual) * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amount = (annual * Decimal(months) / Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amount = max(Decimal("0.00"), min(amount, book_before))
    return DepreciationComputation(amount=amount, annual_amount=annual, rate=rate, months=months)


def run_depreciation(db: Session, run_date: date) -> dict:
    fy_start, fy_end = financial_year_window(db, run_date)
    assets = (
        db.query(FixedAsset)
        .join(FixedAssetType, FixedAsset.asset_type_id == FixedAssetType.id)
        .filter(FixedAsset.status == FixedAssetStatus.REGISTERED)
        .order_by(FixedAsset.asset_number)
        .all()
    )
    journal_lines = []
    updated_assets = []
    total_amount = Decimal("0.00")
    for asset in assets:
        asset_type = asset.asset_type
        if not asset_type or not asset_type.accumulated_depreciation_account_id or not asset_type.depreciation_expense_account_id:
            continue
        computation = compute_period_depreciation(asset, fy_start, fy_end)
        if computation.amount <= 0:
            continue
        if not asset.last_depreciation_run_date or asset.last_depreciation_run_date < fy_start:
            asset.ytd_depreciation = Decimal("0.00")
        asset.accumulated_depreciation = _money(asset.accumulated_depreciation) + computation.amount
        asset.ytd_depreciation = _money(asset.ytd_depreciation) + computation.amount
        asset.last_depreciation_run_date = fy_end
        updated_assets.append(asset)
        total_amount += computation.amount
        journal_lines.append({
            "expense_account_id": asset_type.depreciation_expense_account_id,
            "acc_dep_account_id": asset_type.accumulated_depreciation_account_id,
            "amount": computation.amount,
            "asset_number": asset.asset_number,
            "asset_name": asset.name,
        })

    if not journal_lines:
        return {"run_date": fy_end.isoformat(), "assets_updated": 0, "total_depreciation": 0.0, "transaction_id": None}

    grouped: dict[tuple[int, str], Decimal] = {}
    grouped_credit: dict[tuple[int, str], Decimal] = {}
    for line in journal_lines:
        expense_key = (line["expense_account_id"], "debit")
        credit_key = (line["acc_dep_account_id"], "credit")
        grouped[expense_key] = grouped.get(expense_key, Decimal("0.00")) + line["amount"]
        grouped_credit[credit_key] = grouped_credit.get(credit_key, Decimal("0.00")) + line["amount"]

    entry_lines = []
    for (account_id, _kind), amount in grouped.items():
        entry_lines.append({"account_id": account_id, "debit": amount, "credit": Decimal("0.00"), "description": f"FY depreciation to {fy_end.isoformat()}"})
    for (account_id, _kind), amount in grouped_credit.items():
        entry_lines.append({"account_id": account_id, "debit": Decimal("0.00"), "credit": amount, "description": f"FY depreciation to {fy_end.isoformat()}"})

    txn = create_journal_entry(
        db,
        fy_end,
        f"Fixed asset depreciation run to {fy_end.isoformat()}",
        entry_lines,
        source_type="fixed_asset_depreciation",
        reference=fy_end.isoformat(),
    )
    db.commit()
    return {
        "run_date": fy_end.isoformat(),
        "assets_updated": len(updated_assets),
        "total_depreciation": float(total_amount),
        "transaction_id": txn.id,
    }


def dispose_asset(db: Session, asset_id: int, data: dict) -> dict:
    asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    if asset.status == FixedAssetStatus.DISPOSED:
        raise HTTPException(status_code=400, detail="Fixed asset already disposed")
    disposal_date = _parse_date(data.get("disposal_date")) or date.today()
    disposal_account = _active_account(db, data.get("disposal_account_id"), required=True)
    asset_type = asset.asset_type
    asset_account = _active_account(db, asset_type.asset_account_id, expected_type=AccountType.ASSET, required=True)
    acc_dep_account = _active_account(db, asset_type.accumulated_depreciation_account_id, expected_type=AccountType.ASSET, required=True)
    sale_price = _money(data.get("sale_price"))
    disposal_costs = _money(data.get("disposal_costs"))
    gain_income_account_id = get_default_income_account_id(db, allow_create=False)
    loss_expense_account_id = get_default_expense_account_id(db, allow_create=False)
    total_acc_dep = total_accumulated_depreciation(asset)
    book_value = current_book_value(asset)
    gross_gain_loss = sale_price - book_value
    gain_loss = sale_price - disposal_costs - book_value
    journal_lines = [
        {"account_id": acc_dep_account.id, "debit": total_acc_dep, "credit": Decimal("0.00"), "description": f"Dispose {asset.asset_number}"},
        {"account_id": asset_account.id, "debit": Decimal("0.00"), "credit": _money(asset.purchase_price), "description": f"Dispose {asset.asset_number}"},
    ]
    if sale_price > 0:
        journal_lines.append({"account_id": disposal_account.id, "debit": sale_price, "credit": Decimal("0.00"), "description": f"Proceeds {asset.asset_number}"})
    if disposal_costs > 0:
        expense_account = _active_account(db, loss_expense_account_id, expected_type=AccountType.EXPENSE, required=True)
        journal_lines.append({"account_id": expense_account.id, "debit": disposal_costs, "credit": Decimal("0.00"), "description": f"Disposal costs {asset.asset_number}"})
        journal_lines.append({"account_id": disposal_account.id, "debit": Decimal("0.00"), "credit": disposal_costs, "description": f"Disposal costs paid {asset.asset_number}"})
    if gross_gain_loss > 0:
        income_account = _active_account(db, gain_income_account_id, expected_type=AccountType.INCOME, required=True)
        journal_lines.append({"account_id": income_account.id, "debit": Decimal("0.00"), "credit": gross_gain_loss, "description": f"Gain on disposal {asset.asset_number}"})
    elif gross_gain_loss < 0:
        expense_account = _active_account(db, loss_expense_account_id, expected_type=AccountType.EXPENSE, required=True)
        journal_lines.append({"account_id": expense_account.id, "debit": abs(gross_gain_loss), "credit": Decimal("0.00"), "description": f"Loss on disposal {asset.asset_number}"})

    txn = create_journal_entry(
        db,
        disposal_date,
        f"Fixed asset disposal - {asset.asset_number}",
        journal_lines,
        source_type="fixed_asset_disposal",
        source_id=asset.id,
        reference=asset.asset_number,
    )
    asset.status = FixedAssetStatus.DISPOSED
    asset.disposal_date = disposal_date
    asset.disposal_sale_price = sale_price
    asset.disposal_costs = disposal_costs
    asset.disposal_account_id = disposal_account.id
    asset.disposal_transaction_id = txn.id
    db.commit()
    db.refresh(asset)
    payload = asset_payload(db, asset)
    payload["gain_loss"] = float(gain_loss)
    return payload


def _active_asset_rows(db: Session, as_of_date: date | None = None):
    q = db.query(FixedAsset).join(FixedAssetType, FixedAsset.asset_type_id == FixedAssetType.id)
    if as_of_date:
        q = q.filter(FixedAsset.purchase_date <= as_of_date)
        q = q.filter((FixedAsset.disposal_date == None) | (FixedAsset.disposal_date > as_of_date))
    return q.order_by(FixedAsset.purchase_date.desc(), FixedAsset.asset_number.asc()).all()


def list_assets_payload(db: Session, status: str | None = None) -> list[dict]:
    rows = _active_asset_rows(db)
    if status:
        rows = [row for row in rows if row.status.value == status]
    return [asset_summary_payload(row) for row in rows]


def asset_summary_payload(asset: FixedAsset) -> dict:
    book_value = current_book_value(asset)
    return {
        "id": asset.id,
        "asset_number": asset.asset_number,
        "name": asset.name,
        "status": asset.status.value,
        "asset_type_name": asset.asset_type.name if asset.asset_type else "",
        "purchase_date": asset.purchase_date.isoformat() if asset.purchase_date else None,
        "purchase_price": float(_money(asset.purchase_price)),
        "book_value": float(book_value),
    }


def asset_payload(db: Session, asset: FixedAsset) -> dict:
    asset_type = asset.asset_type
    if asset_type:
        db.refresh(asset_type)
    book_value = current_book_value(asset)
    total_acc_dep = total_accumulated_depreciation(asset)
    return {
        **asset_summary_payload(asset),
        "description": asset.description or "",
        "serial_number": asset.serial_number or "",
        "warranty_expiry": asset.warranty_expiry.isoformat() if asset.warranty_expiry else None,
        "depreciation_start_date": asset.depreciation_start_date.isoformat() if asset.depreciation_start_date else None,
        "cost_limit": float(_money(asset.cost_limit)) if asset.cost_limit is not None else None,
        "residual_value": float(_money(asset.residual_value)),
        "depreciation_method": asset.depreciation_method.value,
        "calculation_basis": asset.calculation_basis.value,
        "averaging_method": asset.averaging_method.value,
        "rate": float(_derived_rate(asset)) if _derived_rate(asset) else None,
        "effective_life_years": float(_effective_life(asset.effective_life_years)) if asset.effective_life_years is not None else None,
        "opening_accumulated_depreciation": float(_money(asset.opening_accumulated_depreciation)),
        "accumulated_depreciation": float(total_acc_dep),
        "accumulated_depreciation_current": float(_money(asset.accumulated_depreciation)),
        "ytd_depreciation": float(_money(asset.ytd_depreciation)),
        "investment_boost": float(_money(asset.investment_boost)) if asset.investment_boost is not None else None,
        "last_depreciation_run_date": asset.last_depreciation_run_date.isoformat() if asset.last_depreciation_run_date else None,
        "acquisition_method": asset.acquisition_method.value,
        "offset_account_id": asset.offset_account_id,
        "offset_account": _account_payload(asset.offset_account),
        "source_reference": asset.source_reference or "",
        "disposal_date": asset.disposal_date.isoformat() if asset.disposal_date else None,
        "disposal_sale_price": float(_money(asset.disposal_sale_price)) if asset.disposal_sale_price is not None else None,
        "disposal_costs": float(_money(asset.disposal_costs)) if asset.disposal_costs is not None else None,
        "disposal_account": _account_payload(asset.disposal_account),
        "asset_type": asset_type_payload(db, asset_type) if asset_type else None,
        "asset_account": _account_payload(asset_type.asset_account if asset_type else None),
        "accumulated_depreciation_account": _account_payload(asset_type.accumulated_depreciation_account if asset_type else None),
        "depreciation_expense_account": _account_payload(asset_type.depreciation_expense_account if asset_type else None),
        "book_value_detail": {
            "cost_basis": float(_money(asset.purchase_price)),
            "book_value": float(book_value),
            "accumulated_depreciation": float(total_acc_dep),
            "ytd_depreciation": float(_money(asset.ytd_depreciation)),
        },
    }


def fixed_asset_reconciliation(db: Session, as_of_date: date) -> dict:
    rows = _active_asset_rows(db, as_of_date=as_of_date)
    assets = []
    total_cost = Decimal("0.00")
    total_acc_dep = Decimal("0.00")
    total_book = Decimal("0.00")
    for asset in rows:
        book = current_book_value(asset)
        accum = total_accumulated_depreciation(asset)
        total_cost += _money(asset.purchase_price)
        total_acc_dep += accum
        total_book += book
        assets.append({
            "asset_number": asset.asset_number,
            "asset_name": asset.name,
            "asset_type": asset.asset_type.name if asset.asset_type else "",
            "purchase_date": asset.purchase_date.isoformat() if asset.purchase_date else None,
            "purchase_price": float(_money(asset.purchase_price)),
            "accumulated_depreciation": float(accum),
            "book_value": float(book),
            "status": asset.status.value,
        })
    return {
        "as_of_date": as_of_date.isoformat(),
        "assets": assets,
        "total_cost": float(total_cost),
        "total_accumulated_depreciation": float(total_acc_dep),
        "total_book_value": float(total_book),
    }


def import_assets_from_csv(db: Session, content: str) -> dict:
    reader = csv.DictReader(StringIO(content))
    imported = 0
    skipped = 0
    created_types = 0
    errors: list[str] = []
    for idx, row in enumerate(reader, start=2):
        name = (row.get("*AssetName") or "").strip()
        number = (row.get("*AssetNumber") or "").strip()
        if not name and not number:
            skipped += 1
            continue
        if not name or not number:
            errors.append(f"Row {idx}: Asset name and asset number are required")
            continue
        if db.query(FixedAsset).filter(FixedAsset.asset_number == number).first():
            errors.append(f"Row {idx}: Asset number {number} already exists")
            continue
        type_name = (row.get("AssetType") or "Imported Asset").strip()
        asset_type = db.query(FixedAssetType).filter(FixedAssetType.name == type_name).first()
        if not asset_type:
            asset_type = FixedAssetType(
                name=type_name,
                description="Created from fixed asset CSV import",
                accumulated_depreciation_account_id=get_fixed_asset_accumulated_depreciation_account_id(db, allow_create=False),
                depreciation_expense_account_id=get_fixed_asset_depreciation_expense_account_id(db, allow_create=False),
            )
            db.add(asset_type)
            db.flush()
            created_types += 1
        accumulated_value = row.get("AccumulatedDepreciation") or row.get("Book_OpeningBookAccumulatedDepreciation")
        if not accumulated_value and row.get("Book_BookValue") not in (None, "") and row.get("PurchasePrice") not in (None, ""):
            accumulated_value = _money(row.get("PurchasePrice")) - _money(row.get("Book_BookValue"))
        asset = FixedAsset(
            asset_number=number,
            name=name,
            asset_type_id=asset_type.id,
            status=FixedAssetStatus.DISPOSED if _parse_date(row.get("DisposalDate")) else FixedAssetStatus.REGISTERED,
            purchase_date=_parse_date(row.get("PurchaseDate")) or date.today(),
            purchase_price=_money(row.get("PurchasePrice")),
            description=(row.get("Description") or "").strip() or None,
            serial_number=(row.get("SerialNumber") or "").strip() or None,
            warranty_expiry=_parse_date(row.get("WarrantyExpiry")),
            depreciation_start_date=_parse_date(row.get("Book_DepreciationStartDate")) or _parse_date(row.get("PurchaseDate")) or date.today(),
            cost_limit=_money(row.get("Book_CostLimit")) if row.get("Book_CostLimit") not in (None, "") else None,
            residual_value=_money(row.get("Book_ResidualValue")),
            depreciation_method=FixedAssetDepreciationMethod.DIMINISHING_VALUE if str(row.get("Book_DepreciationMethod") or "").lower().startswith("d") else FixedAssetDepreciationMethod.STRAIGHT_LINE,
            calculation_basis=FixedAssetCalculationBasis.RATE if row.get("Book_Rate") not in (None, "") else FixedAssetCalculationBasis.EFFECTIVE_LIFE,
            averaging_method=FixedAssetAveragingMethod.FULL_MONTH,
            rate=_rate_value(row.get("Book_Rate")),
            effective_life_years=_effective_life(row.get("Book_EffectiveLife")),
            opening_accumulated_depreciation=_money(accumulated_value),
            accumulated_depreciation=Decimal("0.00"),
            ytd_depreciation=Decimal("0.00"),
            investment_boost=_money(row.get("InvestmentBoost")) if row.get("InvestmentBoost") not in (None, "") else None,
            last_depreciation_run_date=_parse_date(row.get("DepreciationToDate")),
            acquisition_method=FixedAssetAcquisitionMethod.IMPORT_CSV,
            source_reference="CSV import",
            disposal_date=_parse_date(row.get("DisposalDate")),
        )
        db.add(asset)
        imported += 1
    db.commit()
    return {"imported": imported, "skipped": skipped, "created_asset_types": created_types, "errors": errors}


def csv_template_text() -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_HEADERS)
    for _ in range(32):
        writer.writerow([""] * len(TEMPLATE_HEADERS))
    return output.getvalue()

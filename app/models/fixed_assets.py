from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class FixedAssetStatus(str, enum.Enum):
    REGISTERED = "registered"
    DISPOSED = "disposed"


class FixedAssetDepreciationMethod(str, enum.Enum):
    DIMINISHING_VALUE = "dv"
    STRAIGHT_LINE = "sl"


class FixedAssetCalculationBasis(str, enum.Enum):
    RATE = "rate"
    EFFECTIVE_LIFE = "effective_life"


class FixedAssetAveragingMethod(str, enum.Enum):
    FULL_MONTH = "full_month"


class FixedAssetAcquisitionMethod(str, enum.Enum):
    CASH = "cash"
    ACCOUNTS_PAYABLE = "accounts_payable"
    JOURNAL = "journal"
    OPENING_BALANCE = "opening_balance"
    IMPORT_CSV = "import_csv"


class FixedAssetType(Base):
    __tablename__ = "fixed_asset_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    asset_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    accumulated_depreciation_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    depreciation_expense_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    default_depreciation_method = Column(
        Enum(FixedAssetDepreciationMethod),
        nullable=False,
        default=FixedAssetDepreciationMethod.DIMINISHING_VALUE,
    )
    default_calculation_basis = Column(
        Enum(FixedAssetCalculationBasis),
        nullable=False,
        default=FixedAssetCalculationBasis.RATE,
    )
    default_rate = Column(Numeric(8, 4), nullable=True)
    default_effective_life_years = Column(Numeric(8, 2), nullable=True)
    default_cost_limit = Column(Numeric(12, 2), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    asset_account = relationship("Account", foreign_keys=[asset_account_id])
    accumulated_depreciation_account = relationship("Account", foreign_keys=[accumulated_depreciation_account_id])
    depreciation_expense_account = relationship("Account", foreign_keys=[depreciation_expense_account_id])


class FixedAsset(Base):
    __tablename__ = "fixed_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(40), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    asset_type_id = Column(Integer, ForeignKey("fixed_asset_types.id"), nullable=False)
    status = Column(Enum(FixedAssetStatus), nullable=False, default=FixedAssetStatus.REGISTERED)
    purchase_date = Column(Date, nullable=False)
    purchase_price = Column(Numeric(12, 2), nullable=False, default=0)
    description = Column(Text, nullable=True)
    serial_number = Column(String(120), nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    depreciation_start_date = Column(Date, nullable=False)
    cost_limit = Column(Numeric(12, 2), nullable=True)
    residual_value = Column(Numeric(12, 2), nullable=False, default=0)
    depreciation_method = Column(
        Enum(FixedAssetDepreciationMethod),
        nullable=False,
        default=FixedAssetDepreciationMethod.DIMINISHING_VALUE,
    )
    calculation_basis = Column(
        Enum(FixedAssetCalculationBasis),
        nullable=False,
        default=FixedAssetCalculationBasis.RATE,
    )
    averaging_method = Column(
        Enum(FixedAssetAveragingMethod),
        nullable=False,
        default=FixedAssetAveragingMethod.FULL_MONTH,
    )
    rate = Column(Numeric(8, 4), nullable=True)
    effective_life_years = Column(Numeric(8, 2), nullable=True)
    opening_accumulated_depreciation = Column(Numeric(12, 2), nullable=False, default=0)
    accumulated_depreciation = Column(Numeric(12, 2), nullable=False, default=0)
    ytd_depreciation = Column(Numeric(12, 2), nullable=False, default=0)
    investment_boost = Column(Numeric(12, 2), nullable=True)
    last_depreciation_run_date = Column(Date, nullable=True)
    acquisition_method = Column(
        Enum(FixedAssetAcquisitionMethod),
        nullable=False,
        default=FixedAssetAcquisitionMethod.CASH,
    )
    offset_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    acquisition_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    source_reference = Column(String(120), nullable=True)
    disposal_date = Column(Date, nullable=True)
    disposal_sale_price = Column(Numeric(12, 2), nullable=True)
    disposal_costs = Column(Numeric(12, 2), nullable=True)
    disposal_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    disposal_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    asset_type = relationship("FixedAssetType", foreign_keys=[asset_type_id])
    offset_account = relationship("Account", foreign_keys=[offset_account_id])
    disposal_account = relationship("Account", foreign_keys=[disposal_account_id])
    acquisition_transaction = relationship("Transaction", foreign_keys=[acquisition_transaction_id])
    disposal_transaction = relationship("Transaction", foreign_keys=[disposal_transaction_id])

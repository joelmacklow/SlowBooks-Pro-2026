"""add fixed assets module

Revision ID: u1j2k3l4m5n6
Revises: t0i1j2k3l4m5
Create Date: 2026-04-23 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u1j2k3l4m5n6"
down_revision: Union[str, None] = "t0i1j2k3l4m5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fixed_asset_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("asset_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("accumulated_depreciation_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("depreciation_expense_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("default_depreciation_method", sa.Enum("DIMINISHING_VALUE", "STRAIGHT_LINE", name="fixedassetdepreciationmethod"), nullable=False, server_default="DIMINISHING_VALUE"),
        sa.Column("default_calculation_basis", sa.Enum("RATE", "EFFECTIVE_LIFE", name="fixedassetcalculationbasis"), nullable=False, server_default="RATE"),
        sa.Column("default_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("default_effective_life_years", sa.Numeric(8, 2), nullable=True),
        sa.Column("default_cost_limit", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fixed_asset_types_id", "fixed_asset_types", ["id"])

    op.create_table(
        "fixed_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_number", sa.String(length=40), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("asset_type_id", sa.Integer(), sa.ForeignKey("fixed_asset_types.id"), nullable=False),
        sa.Column("status", sa.Enum("REGISTERED", "DISPOSED", name="fixedassetstatus"), nullable=False, server_default="REGISTERED"),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("warranty_expiry", sa.Date(), nullable=True),
        sa.Column("depreciation_start_date", sa.Date(), nullable=False),
        sa.Column("cost_limit", sa.Numeric(12, 2), nullable=True),
        sa.Column("residual_value", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("depreciation_method", sa.Enum("DIMINISHING_VALUE", "STRAIGHT_LINE", name="fixedassetdepreciationmethod"), nullable=False, server_default="DIMINISHING_VALUE"),
        sa.Column("calculation_basis", sa.Enum("RATE", "EFFECTIVE_LIFE", name="fixedassetcalculationbasis"), nullable=False, server_default="RATE"),
        sa.Column("averaging_method", sa.Enum("FULL_MONTH", name="fixedassetaveragingmethod"), nullable=False, server_default="FULL_MONTH"),
        sa.Column("rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("effective_life_years", sa.Numeric(8, 2), nullable=True),
        sa.Column("opening_accumulated_depreciation", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("accumulated_depreciation", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ytd_depreciation", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("investment_boost", sa.Numeric(12, 2), nullable=True),
        sa.Column("last_depreciation_run_date", sa.Date(), nullable=True),
        sa.Column("acquisition_method", sa.Enum("CASH", "ACCOUNTS_PAYABLE", "JOURNAL", "OPENING_BALANCE", "IMPORT_CSV", name="fixedassetacquisitionmethod"), nullable=False, server_default="CASH"),
        sa.Column("offset_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("acquisition_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("source_reference", sa.String(length=120), nullable=True),
        sa.Column("disposal_date", sa.Date(), nullable=True),
        sa.Column("disposal_sale_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("disposal_costs", sa.Numeric(12, 2), nullable=True),
        sa.Column("disposal_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("disposal_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fixed_assets_id", "fixed_assets", ["id"])


def downgrade() -> None:
    op.drop_index("ix_fixed_assets_id", table_name="fixed_assets")
    op.drop_table("fixed_assets")
    op.drop_index("ix_fixed_asset_types_id", table_name="fixed_asset_types")
    op.drop_table("fixed_asset_types")

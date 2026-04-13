"""implement nz paye pay runs

Revision ID: e5f6a7b8c9d0
Revises: d4e1f2a3b4c5
Create Date: 2026-04-14 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("child_support_amount", sa.Numeric(precision=12, scale=2), server_default="0.00", nullable=True))
        batch_op.alter_column("kiwisaver_rate", server_default="0.0350", existing_type=sa.Numeric(precision=6, scale=4))

    op.execute("UPDATE employees SET child_support_amount = '0.00' WHERE child_support_amount IS NULL")

    with op.batch_alter_table("employees") as batch_op:
        batch_op.alter_column("child_support_amount", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))

    with op.batch_alter_table("pay_runs") as batch_op:
        batch_op.add_column(sa.Column("tax_year", sa.Integer(), server_default="2027", nullable=False))
        batch_op.add_column(sa.Column("total_paye", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("total_acc_earners_levy", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("total_student_loan", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("total_kiwisaver_employee", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("total_employer_kiwisaver", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("total_esct", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("total_child_support", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))

    with op.batch_alter_table("pay_runs") as batch_op:
        batch_op.alter_column("tax_year", server_default=None, existing_type=sa.Integer())
        batch_op.alter_column("total_paye", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("total_acc_earners_levy", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("total_student_loan", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("total_kiwisaver_employee", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("total_employer_kiwisaver", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("total_esct", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("total_child_support", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))

    with op.batch_alter_table("pay_stubs") as batch_op:
        batch_op.add_column(sa.Column("tax_code", sa.String(length=20), server_default="M", nullable=False))
        batch_op.add_column(sa.Column("paye", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("acc_earners_levy", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("student_loan_deduction", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("kiwisaver_employee_deduction", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("employer_kiwisaver_contribution", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("esct", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.add_column(sa.Column("child_support_deduction", sa.Numeric(precision=12, scale=2), server_default="0", nullable=True))
        batch_op.drop_column("federal_tax")
        batch_op.drop_column("state_tax")
        batch_op.drop_column("ss_tax")
        batch_op.drop_column("medicare_tax")

    with op.batch_alter_table("pay_stubs") as batch_op:
        batch_op.alter_column("tax_code", server_default=None, existing_type=sa.String(length=20))
        batch_op.alter_column("paye", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("acc_earners_levy", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("student_loan_deduction", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("kiwisaver_employee_deduction", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("employer_kiwisaver_contribution", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("esct", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))
        batch_op.alter_column("child_support_deduction", server_default=None, existing_type=sa.Numeric(precision=12, scale=2))


def downgrade() -> None:
    with op.batch_alter_table("pay_stubs") as batch_op:
        batch_op.add_column(sa.Column("medicare_tax", sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column("ss_tax", sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column("state_tax", sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.add_column(sa.Column("federal_tax", sa.Numeric(precision=12, scale=2), nullable=True))
        batch_op.drop_column("child_support_deduction")
        batch_op.drop_column("esct")
        batch_op.drop_column("employer_kiwisaver_contribution")
        batch_op.drop_column("kiwisaver_employee_deduction")
        batch_op.drop_column("student_loan_deduction")
        batch_op.drop_column("acc_earners_levy")
        batch_op.drop_column("paye")
        batch_op.drop_column("tax_code")

    with op.batch_alter_table("pay_runs") as batch_op:
        batch_op.drop_column("total_child_support")
        batch_op.drop_column("total_esct")
        batch_op.drop_column("total_employer_kiwisaver")
        batch_op.drop_column("total_kiwisaver_employee")
        batch_op.drop_column("total_student_loan")
        batch_op.drop_column("total_acc_earners_levy")
        batch_op.drop_column("total_paye")
        batch_op.drop_column("tax_year")

    with op.batch_alter_table("employees") as batch_op:
        batch_op.alter_column("kiwisaver_rate", server_default="0.0300", existing_type=sa.Numeric(precision=6, scale=4))
        batch_op.drop_column("child_support_amount")

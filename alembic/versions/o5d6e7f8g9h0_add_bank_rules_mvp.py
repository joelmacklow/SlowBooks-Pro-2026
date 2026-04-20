"""compatibility placeholder for removed bank rules mvp revision

Revision ID: o5d6e7f8g9h0
Revises: n4c5d6e7f8g9
Create Date: 2026-04-20 15:05:00.000000

This revision intentionally acts as a no-op on `main`.

The original Bank Rules MVP branch introduced this revision id before that
feature branch was closed without merging to main. Some environments were
already stamped with `o5d6e7f8g9h0`, which means Alembic on current `main`
must still be able to resolve that revision during bootstrap.

Keeping this compatibility placeholder restores a linear migration chain
without reintroducing the unmerged Bank Rules schema to `main`.
"""

from typing import Sequence, Union


revision: str = "o5d6e7f8g9h0"
down_revision: Union[str, None] = "n4c5d6e7f8g9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Compatibility no-op: intentionally left blank on main.
    pass


def downgrade() -> None:
    # Compatibility no-op: intentionally left blank on main.
    pass

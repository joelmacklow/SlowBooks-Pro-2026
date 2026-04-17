from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.schemas.journal import JournalEntryResponse


class OpeningBalanceStatusResponse(BaseModel):
    is_ready: bool
    source: Optional[str] = None
    ready_at: Optional[str] = None


class OpeningBalanceLineCreate(BaseModel):
    account_id: int
    amount: Decimal = Decimal("0")


class OpeningBalanceCreate(BaseModel):
    date: date
    description: Optional[str] = None
    reference: Optional[str] = None
    auto_balance_account_id: Optional[int] = None
    lines: list[OpeningBalanceLineCreate]


class OpeningBalanceCreateResponse(BaseModel):
    journal: JournalEntryResponse

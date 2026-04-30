from datetime import datetime
from decimal import Decimal
import re
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.items import ItemType


class ItemCreate(BaseModel):
    code: Optional[str] = None
    name: str
    item_type: ItemType
    description: Optional[str] = None
    rate: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    vendor_id: Optional[int] = None
    income_account_id: Optional[int] = None
    expense_account_id: Optional[int] = None
    is_taxable: bool = True

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not re.fullmatch(r"[0-9-]+", value):
            raise ValueError("Code may contain only numbers and dashes")
        return value


class ItemUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    item_type: Optional[ItemType] = None
    description: Optional[str] = None
    rate: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    vendor_id: Optional[int] = None
    income_account_id: Optional[int] = None
    expense_account_id: Optional[int] = None
    is_taxable: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not re.fullmatch(r"[0-9-]+", value):
            raise ValueError("Code may contain only numbers and dashes")
        return value


class ItemResponse(BaseModel):
    id: int
    code: Optional[str]
    name: str
    item_type: ItemType
    description: Optional[str]
    rate: Decimal
    cost: Decimal
    vendor_id: Optional[int]
    income_account_id: Optional[int]
    expense_account_id: Optional[int]
    is_taxable: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

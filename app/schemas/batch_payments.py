from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class BatchPaymentAllocationCreate(BaseModel):
    customer_id: int
    invoice_id: int
    amount: Decimal
    date: Optional[date_type] = None


class BatchPaymentCreate(BaseModel):
    date: Optional[date_type] = None
    method: Optional[str] = None
    check_number: Optional[str] = None
    reference: Optional[str] = None
    deposit_to_account_id: Optional[int] = None
    notes: Optional[str] = None
    allocations: list[BatchPaymentAllocationCreate] = []

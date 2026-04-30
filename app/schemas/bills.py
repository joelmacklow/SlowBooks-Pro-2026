from datetime import date as date_type, datetime as datetime_type
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class BillLineCreate(BaseModel):
    item_id: Optional[int] = None
    account_id: Optional[int] = None
    description: Optional[str] = None
    quantity: float = 1
    rate: float = 0
    gst_code: str = "GST15"
    gst_rate: Decimal = Decimal("0.1500")
    line_order: int = 0


class BillLineResponse(BaseModel):
    id: int
    item_id: Optional[int] = None
    account_id: Optional[int] = None
    description: Optional[str] = None
    quantity: float = 1
    rate: float = 0
    amount: float = 0
    gst_code: str = "GST15"
    gst_rate: Decimal = Decimal("0.1500")
    line_order: int = 0
    model_config = {"from_attributes": True}


class BillCreate(BaseModel):
    vendor_id: int
    bill_number: str
    date: date_type
    due_date: Optional[date_type] = None
    terms: str = "Net 30"
    ref_number: Optional[str] = None
    po_id: Optional[int] = None
    tax_rate: float = 0
    notes: Optional[str] = None
    lines: list[BillLineCreate] = []


class BillUpdate(BaseModel):
    bill_number: Optional[str] = None
    date: Optional[date_type] = None
    due_date: Optional[date_type] = None
    terms: Optional[str] = None
    ref_number: Optional[str] = None
    tax_rate: Optional[float] = None
    notes: Optional[str] = None
    lines: Optional[list[BillLineCreate]] = None


class BillResponse(BaseModel):
    id: int
    bill_number: str
    vendor_id: int
    vendor_name: Optional[str] = None
    status: str
    po_id: Optional[int] = None
    date: date_type
    due_date: Optional[date_type] = None
    terms: Optional[str] = None
    ref_number: Optional[str] = None
    subtotal: float = 0
    tax_rate: float = 0
    tax_amount: float = 0
    total: float = 0
    amount_paid: float = 0
    balance_due: float = 0
    notes: Optional[str] = None
    lines: list[BillLineResponse] = []
    created_at: Optional[datetime_type] = None
    model_config = {"from_attributes": True}


class BillPaymentAllocationCreate(BaseModel):
    bill_id: int
    amount: float


class BillPaymentCreate(BaseModel):
    vendor_id: int
    date: date_type
    amount: float
    method: Optional[str] = None
    check_number: Optional[str] = None
    pay_from_account_id: Optional[int] = None
    notes: Optional[str] = None
    allocations: list[BillPaymentAllocationCreate] = []


class BillPaymentResponse(BaseModel):
    id: int
    vendor_id: int
    vendor_name: Optional[str] = None
    date: date_type
    amount: float
    allocated_amount: float = 0
    unallocated_amount: float = 0
    method: Optional[str] = None
    check_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime_type] = None
    model_config = {"from_attributes": True}

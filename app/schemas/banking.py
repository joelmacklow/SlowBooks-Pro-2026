from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.banking import BankRuleDirection, ReconciliationStatus


class BankAccountCreate(BaseModel):
    name: str
    account_id: Optional[int] = None
    bank_name: Optional[str] = None
    last_four: Optional[str] = None
    balance: Decimal = Decimal("0")


class BankAccountUpdate(BaseModel):
    name: Optional[str] = None
    account_id: Optional[int] = None
    bank_name: Optional[str] = None
    last_four: Optional[str] = None
    is_active: Optional[bool] = None


class BankAccountResponse(BaseModel):
    id: int
    name: str
    account_id: Optional[int]
    bank_name: Optional[str]
    last_four: Optional[str]
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BankTransactionCreate(BaseModel):
    bank_account_id: int
    date: date
    amount: Decimal
    payee: Optional[str] = None
    description: Optional[str] = None
    check_number: Optional[str] = None
    reference: Optional[str] = None
    code: Optional[str] = None
    category_account_id: Optional[int] = None


class BankTransactionResponse(BaseModel):
    id: int
    bank_account_id: int
    date: date
    amount: Decimal
    payee: Optional[str]
    description: Optional[str]
    check_number: Optional[str]
    reference: Optional[str]
    code: Optional[str]
    category_account_id: Optional[int]
    reconciled: bool
    transaction_id: Optional[int]
    match_status: Optional[str]
    import_batch_id: Optional[str]
    suggested_rule_id: Optional[int]
    suggested_account_id: Optional[int]
    rule_match_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class BankTransactionMatchApproval(BaseModel):
    match_kind: str
    target_id: int


class BankTransactionCodeApproval(BaseModel):
    account_id: int
    description: Optional[str] = None


class BankTransactionSplitLine(BaseModel):
    account_id: int
    amount: Decimal
    description: Optional[str] = None
    gst_code: Optional[str] = None
    gst_rate: Optional[Decimal] = None


class BankTransactionSplitCodeApproval(BaseModel):
    splits: list[BankTransactionSplitLine]
    use_purchase_gst: bool = False


class BankTransactionRuleApproval(BaseModel):
    rule_id: Optional[int] = None


class BankRuleCreate(BaseModel):
    name: str
    priority: int = 100
    is_active: bool = True
    bank_account_id: Optional[int] = None
    direction: BankRuleDirection = BankRuleDirection.ANY
    payee_contains: Optional[str] = None
    description_contains: Optional[str] = None
    reference_contains: Optional[str] = None
    code_equals: Optional[str] = None
    target_account_id: int
    default_description: Optional[str] = None


class BankRuleUpdate(BaseModel):
    name: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    bank_account_id: Optional[int] = None
    direction: Optional[BankRuleDirection] = None
    payee_contains: Optional[str] = None
    description_contains: Optional[str] = None
    reference_contains: Optional[str] = None
    code_equals: Optional[str] = None
    target_account_id: Optional[int] = None
    default_description: Optional[str] = None


class BankRuleResponse(BaseModel):
    id: int
    name: str
    priority: int
    is_active: bool
    bank_account_id: Optional[int]
    direction: BankRuleDirection
    payee_contains: Optional[str]
    description_contains: Optional[str]
    reference_contains: Optional[str]
    code_equals: Optional[str]
    target_account_id: int
    default_description: Optional[str]
    bank_account_name: Optional[str] = None
    target_account_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReconciliationCreate(BaseModel):
    bank_account_id: int
    statement_date: date
    statement_balance: Decimal
    import_batch_id: Optional[str] = None


class ReconciliationResponse(BaseModel):
    id: int
    bank_account_id: int
    statement_date: date
    statement_balance: Decimal
    import_batch_id: Optional[str]
    status: ReconciliationStatus
    created_at: datetime
    completed_at: Optional[datetime]
    balance_applied_at: Optional[datetime]

    model_config = {"from_attributes": True}

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


TimingDirection = Literal["before_due", "after_due"]
ReminderStatus = Literal["sent", "failed", "skipped"]
TriggerType = Literal["manual", "automatic"]


class InvoiceReminderRuleCreate(BaseModel):
    name: Optional[str] = None
    timing_direction: TimingDirection
    day_offset: int = Field(ge=0, le=365)
    is_enabled: bool = True
    sort_order: Optional[int] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None

    @field_validator("name", "subject_template", "body_template")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class InvoiceReminderRuleUpdate(BaseModel):
    name: Optional[str] = None
    timing_direction: Optional[TimingDirection] = None
    day_offset: Optional[int] = Field(default=None, ge=0, le=365)
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None

    @field_validator("name", "subject_template", "body_template")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class InvoiceReminderRuleResponse(BaseModel):
    id: int
    name: str
    timing_direction: TimingDirection
    day_offset: int
    is_enabled: bool
    sort_order: int
    subject_template: str
    body_template: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceReminderPreviewItem(BaseModel):
    invoice_id: int
    invoice_number: str
    customer_id: int
    customer_name: str
    recipient: str
    due_date: date
    balance_due: Decimal
    days_from_due: int
    rule_id: int
    rule_name: str
    timing_direction: TimingDirection
    day_offset: int
    last_reminder_sent_at: Optional[datetime] = None
    last_reminder_status: Optional[ReminderStatus] = None
    last_reminder_trigger_type: Optional[TriggerType] = None
    last_reminder_detail: Optional[str] = None


class InvoiceReminderPreviewResponse(BaseModel):
    as_of_date: date
    items: list[InvoiceReminderPreviewItem]
    item_count: int

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


SUPPORTED_TIMESHEET_ENTRY_MODES = {"duration", "start_end"}
SUPPORTED_TIMESHEET_STATUSES = {"draft", "submitted", "approved", "rejected", "locked"}


def _normalize_entry_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    if mode not in SUPPORTED_TIMESHEET_ENTRY_MODES:
        raise ValueError("Unsupported timesheet entry mode")
    return mode


class TimesheetLineUpsert(BaseModel):
    work_date: date
    entry_mode: str = "duration"
    duration_hours: Optional[Decimal] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_minutes: int = 0
    notes: Optional[str] = None

    @field_validator("entry_mode")
    @classmethod
    def validate_entry_mode(cls, value: str) -> str:
        return _normalize_entry_mode(value)

    @field_validator("break_minutes")
    @classmethod
    def validate_break_minutes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Break minutes must be non-negative")
        return value


class TimesheetCreateRequest(BaseModel):
    employee_id: int
    period_start: date
    period_end: date
    lines: list[TimesheetLineUpsert]


class TimesheetSelfCreateRequest(BaseModel):
    period_start: date
    period_end: date
    lines: list[TimesheetLineUpsert]

    model_config = {"extra": "forbid"}


class TimesheetUpdateRequest(BaseModel):
    lines: list[TimesheetLineUpsert]


class TimesheetStatusActionRequest(BaseModel):
    reason: Optional[str] = None


class TimesheetCorrectionRequest(BaseModel):
    lines: list[TimesheetLineUpsert]
    reason: str

    model_config = {"extra": "forbid"}


class TimesheetBulkApproveRequest(BaseModel):
    timesheet_ids: list[int]

    model_config = {"extra": "forbid"}


class TimesheetLineResponse(BaseModel):
    id: int
    work_date: date
    entry_mode: str
    duration_hours: Optional[Decimal] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_minutes: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class TimesheetAuditEventResponse(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    status_from: Optional[str] = None
    status_to: Optional[str] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TimesheetListResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    pay_run_id: Optional[int] = None
    period_start: date
    period_end: date
    status: str
    total_hours: Decimal
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = str(value).lower()
        if normalized not in SUPPORTED_TIMESHEET_STATUSES:
            raise ValueError("Unsupported timesheet status")
        return normalized


class TimesheetDetailResponse(TimesheetListResponse):
    lines: list[TimesheetLineResponse] = Field(default_factory=list)
    audit_events: list[TimesheetAuditEventResponse] = Field(default_factory=list)


class TimesheetReadinessResponse(BaseModel):
    period_start: date
    period_end: date
    pay_run_id: Optional[int] = None
    draft: list[TimesheetListResponse] = Field(default_factory=list)
    submitted: list[TimesheetListResponse] = Field(default_factory=list)
    approved: list[TimesheetListResponse] = Field(default_factory=list)
    rejected: list[TimesheetListResponse] = Field(default_factory=list)
    locked: list[TimesheetListResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}

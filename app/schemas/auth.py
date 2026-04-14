from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BootstrapAdminRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Invalid email")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Invalid email")
        return value


class UserCreateRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str
    role_key: str
    allow_permissions: list[str] = []
    deny_permissions: list[str] = []
    is_active: bool = True

    @field_validator("allow_permissions", "deny_permissions")
    @classmethod
    def dedupe_permissions(cls, value: list[str]) -> list[str]:
        seen = []
        for item in value:
            if item not in seen:
                seen.append(item)
        return seen

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Invalid email")
        return value


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    role_key: Optional[str] = None
    allow_permissions: Optional[list[str]] = None
    deny_permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None
    membership_active: Optional[bool] = None


class MembershipResponse(BaseModel):
    company_scope: str
    role_key: str
    is_active: bool
    allow_permissions: list[str] = []
    deny_permissions: list[str] = []
    effective_permissions: list[str] = []


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    membership: MembershipResponse
    created_at: Optional[datetime] = None


class AuthSessionResponse(BaseModel):
    token: str
    user: UserResponse


class CurrentSessionResponse(BaseModel):
    authenticated: bool
    bootstrap_required: bool = False
    user: Optional[UserResponse] = None


class RoleTemplateResponse(BaseModel):
    key: str
    label: str
    description: str
    permissions: list[str]


class PermissionDefinitionResponse(BaseModel):
    key: str
    description: str


class AuthMetaResponse(BaseModel):
    roles: list[RoleTemplateResponse]
    permissions: list[PermissionDefinitionResponse]

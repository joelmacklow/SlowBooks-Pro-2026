from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    memberships = relationship("UserMembership", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    employee_links = relationship(
        "EmployeePortalLink",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="EmployeePortalLink.user_id",
    )


class UserMembership(Base):
    __tablename__ = "user_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "company_scope", name="uq_user_memberships_user_scope"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_scope = Column(String(100), nullable=False, default="__current__")
    role_key = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="memberships")
    permission_overrides = relationship(
        "MembershipPermissionOverride",
        back_populates="membership",
        cascade="all, delete-orphan",
    )


class MembershipPermissionOverride(Base):
    __tablename__ = "membership_permission_overrides"
    __table_args__ = (
        UniqueConstraint("membership_id", "permission_key", name="uq_membership_permission_override"),
    )

    id = Column(Integer, primary_key=True, index=True)
    membership_id = Column(Integer, ForeignKey("user_memberships.id", ondelete="CASCADE"), nullable=False)
    permission_key = Column(String(120), nullable=False)
    is_allowed = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    membership = relationship("UserMembership", back_populates="permission_overrides")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    company_scope = Column(String(100), nullable=False, default="__current__")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")


class EmployeePortalLink(Base):
    __tablename__ = "employee_portal_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_scope = Column(String(100), nullable=False)
    employee_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deactivated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="employee_links", foreign_keys=[user_id])

    __table_args__ = (
        Index(
            "uq_employee_portal_links_user_scope_active",
            "user_id",
            "company_scope",
            unique=True,
            sqlite_where=is_active.is_(True),
            postgresql_where=is_active.is_(True),
        ),
        Index(
            "uq_employee_portal_links_scope_employee_active",
            "company_scope",
            "employee_id",
            unique=True,
            sqlite_where=is_active.is_(True),
            postgresql_where=is_active.is_(True),
        ),
    )

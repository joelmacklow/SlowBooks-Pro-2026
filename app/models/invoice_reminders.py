from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class InvoiceReminderRule(Base):
    __tablename__ = "invoice_reminder_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    timing_direction = Column(String(20), nullable=False)  # before_due, after_due
    day_offset = Column(Integer, nullable=False, default=0)
    is_enabled = Column(Boolean, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
    subject_template = Column(String(500), nullable=False)
    body_template = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvoiceReminderAudit(Base):
    __tablename__ = "invoice_reminder_audit"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("invoice_reminder_rules.id"), nullable=False)
    email_log_id = Column(Integer, ForeignKey("email_log.id"), nullable=True)
    recipient = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False)  # sent, failed, skipped
    trigger_type = Column(String(20), nullable=False)  # manual, automatic
    scheduled_for_date = Column(Date, nullable=False)
    days_from_due_snapshot = Column(Integer, nullable=False)
    balance_due_snapshot = Column(Numeric(12, 2), nullable=False, default=0)
    detail = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice")
    customer = relationship("Customer")
    rule = relationship("InvoiceReminderRule")
    email_log = relationship("EmailLog")

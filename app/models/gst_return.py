import enum

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Enum, UniqueConstraint, func

from app.database import Base


class GstReturnStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    VOIDED = "voided"


class GstReturn(Base):
    __tablename__ = "gst_returns"
    __table_args__ = (
        UniqueConstraint("start_date", "end_date", name="uq_gst_returns_period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    gst_basis = Column(String(20), nullable=False)
    gst_period = Column(String(20), nullable=False)
    net_position = Column(String(20), nullable=False)
    box5 = Column(Numeric(12, 2), nullable=False)
    box6 = Column(Numeric(12, 2), nullable=False)
    box7 = Column(Numeric(12, 2), nullable=False)
    box8 = Column(Numeric(12, 2), nullable=False)
    box9 = Column(Numeric(12, 2), nullable=False)
    box10 = Column(Numeric(12, 2), nullable=False)
    box11 = Column(Numeric(12, 2), nullable=False)
    box12 = Column(Numeric(12, 2), nullable=False)
    box13 = Column(Numeric(12, 2), nullable=False)
    box14 = Column(Numeric(12, 2), nullable=False)
    box15 = Column(Numeric(12, 2), nullable=False)
    output_gst = Column(Numeric(12, 2), nullable=False)
    input_gst = Column(Numeric(12, 2), nullable=False)
    net_gst = Column(Numeric(12, 2), nullable=False)
    box9_adjustments = Column(Numeric(12, 2), default=0, nullable=False)
    box13_adjustments = Column(Numeric(12, 2), default=0, nullable=False)
    status = Column(Enum(GstReturnStatus), default=GstReturnStatus.CONFIRMED, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

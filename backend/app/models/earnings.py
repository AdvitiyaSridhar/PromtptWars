import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from app.database import Base

class EarningsLedger(Base):
    __tablename__ = "earnings_ledger"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    shift_id = Column(String(36), ForeignKey("shifts.id"), unique=True, nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    regular_hours = Column(Numeric(6, 2), nullable=False, default=0.00)
    overtime_hours = Column(Numeric(6, 2), nullable=False, default=0.00)
    gross_pay = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_deductions = Column(Numeric(10, 2), nullable=False, default=0.00)
    net_pay = Column(Numeric(10, 2), nullable=False, default=0.00)  # Invariant: gross_pay - total_deductions
    currency = Column(String(10), nullable=False, default="USD")
    payment_status = Column(String(50), nullable=False, default="pending")  # "pending", "approved", "paid"
    paid_at = Column(DateTime, nullable=True)
    payment_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    shift = relationship("Shift", back_populates="ledger_entry")
    worker = relationship("User", foreign_keys=[worker_id])
    deductions = relationship("Deduction", back_populates="ledger", cascade="all, delete-orphan")
    disputes = relationship("PayDispute", back_populates="ledger")


class Deduction(Base):
    __tablename__ = "deductions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ledger_id = Column(String(36), ForeignKey("earnings_ledger.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # "equipment_rental", "uniform", "transport", "advance", "other"
    amount = Column(Numeric(10, 2), nullable=False)  # Invariant: amount > 0
    description = Column(String(255), nullable=False)
    authorization_doc_ref = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    ledger = relationship("EarningsLedger", back_populates="deductions")

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from app.database import Base

class PayDispute(Base):
    __tablename__ = "pay_disputes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    shift_id = Column(String(36), ForeignKey("shifts.id"), nullable=False, index=True)
    ledger_id = Column(String(36), ForeignKey("earnings_ledger.id"), nullable=True, index=True)
    dispute_type = Column(String(50), nullable=False)  # "unpaid_hours", "unauthorized_deduction", "wrong_rate", "missing_break"
    claimed_amount = Column(Numeric(10, 2), nullable=False)
    worker_explanation = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="submitted")  # "submitted", "under_review", "evidence_requested", "resolved_upheld", "resolved_rejected"
    settled_amount = Column(Numeric(10, 2), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    worker = relationship("User", foreign_keys=[worker_id], back_populates="disputes")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    shift = relationship("Shift", back_populates="disputes")
    ledger = relationship("EarningsLedger", back_populates="disputes")

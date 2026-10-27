import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Numeric, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    workplace_id = Column(String(36), ForeignKey("workplaces.id"), nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False, index=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    base_hourly_rate = Column(Numeric(10, 2), nullable=False, default=25.00)
    overtime_rate_multiplier = Column(Numeric(4, 2), nullable=False, default=1.50)
    status = Column(String(50), nullable=False, default="scheduled")  # "scheduled", "in_progress", "completed", "cancelled"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    worker = relationship("User", foreign_keys=[worker_id], back_populates="shifts")
    creator = relationship("User", foreign_keys=[created_by])
    workplace = relationship("Workplace", back_populates="shifts")
    checkin_events = relationship("CheckinEvent", back_populates="shift", cascade="all, delete-orphan")
    ledger_entry = relationship("EarningsLedger", back_populates="shift", uselist=False, cascade="all, delete-orphan")
    disputes = relationship("PayDispute", back_populates="shift")


class CheckinEvent(Base):
    __tablename__ = "checkin_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    shift_id = Column(String(36), ForeignKey("shifts.id"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    workplace_id = Column(String(36), ForeignKey("workplaces.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # "check_in", "check_out"
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    verification_status = Column(String(50), nullable=False)  # "verified", "rejected_fatigue", "rejected_window", "rejected_site"
    scanned_site_token = Column(String(255), nullable=True)
    recorded_latitude = Column(Float, nullable=True)
    recorded_longitude = Column(Float, nullable=True)
    details = Column(Text, nullable=True)

    # Relationships
    shift = relationship("Shift", back_populates="checkin_events")


class FatigueExceptionLog(Base):
    __tablename__ = "fatigue_exception_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    shift_id = Column(String(36), ForeignKey("shifts.id"), nullable=True)
    workplace_id = Column(String(36), ForeignKey("workplaces.id"), nullable=False)
    attempted_action = Column(String(50), nullable=False)  # "shift_assignment", "qr_check_in"
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    breach_type = Column(String(50), nullable=False)  # "insufficient_rest", "daily_hours_exceeded", "weekly_hours_exceeded", "overlapping_shifts"
    hours_worked_past_24h = Column(Float, nullable=False, default=0.0)
    rest_hours_elapsed = Column(Float, nullable=False, default=0.0)
    policy_required_rest = Column(Float, nullable=False, default=0.0)
    policy_max_daily = Column(Float, nullable=False, default=0.0)
    rejection_reason = Column(Text, nullable=False)
    reviewed_by_admin = Column(Boolean, default=False, nullable=False)
    admin_audit_notes = Column(Text, nullable=True)

    # Relationships
    worker = relationship("User", foreign_keys=[worker_id])
    workplace = relationship("Workplace", foreign_keys=[workplace_id])


class AttendanceAttempt(Base):
    __tablename__ = "attendance_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    workplace_id = Column(String(36), ForeignKey("workplaces.id"), nullable=True, index=True)
    shift_id = Column(String(36), ForeignKey("shifts.id"), nullable=True, index=True)
    attempted_action = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    outcome_code = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)

    worker = relationship("User")
    workplace = relationship("Workplace")
    shift = relationship("Shift")

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Date
from sqlalchemy.orm import relationship
from app.database import Base

class SafetyReport(Base):
    __tablename__ = "safety_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    workplace_id = Column(String(36), ForeignKey("workplaces.id"), nullable=False, index=True)
    shift_id = Column(String(36), ForeignKey("shifts.id"), nullable=True)
    category = Column(String(50), nullable=False)  # "hazard", "near_miss", "injury", "heat_stress", "ppe_shortage", "equipment_defect"
    severity = Column(String(50), nullable=False, default="medium")  # "low", "medium", "high", "critical"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    status = Column(String(50), nullable=False, default="submitted")  # "submitted", "investigating", "corrective_action_pending", "resolved", "closed"
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="safety_reports")
    assignee = relationship("User", foreign_keys=[assigned_to])
    workplace = relationship("Workplace", back_populates="safety_reports")
    actions = relationship("SafetyAction", back_populates="report", cascade="all, delete-orphan")


class SafetyAction(Base):
    __tablename__ = "safety_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey("safety_reports.id"), nullable=False, index=True)
    action_description = Column(Text, nullable=False)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=False)
    due_date = Column(Date, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    report = relationship("SafetyReport", back_populates="actions")
    assignee = relationship("User", foreign_keys=[assigned_to])
    verifier = relationship("User", foreign_keys=[verified_by])

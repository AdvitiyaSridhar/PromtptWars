import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="worker")  # "worker", "employer_admin", "safety_officer"
    industry_sector = Column(String(50), nullable=False, default="construction")  # "construction", "gig_platform"
    phone_number = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    shifts = relationship("Shift", back_populates="worker", foreign_keys="Shift.worker_id")
    organization = relationship("Organization")
    safety_reports = relationship("SafetyReport", back_populates="reporter", foreign_keys="SafetyReport.reporter_id")
    disputes = relationship("PayDispute", back_populates="worker", foreign_keys="PayDispute.worker_id")

    @property
    def organization_name(self):
        return self.organization.name if self.organization else None

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Workplace(Base):
    __tablename__ = "workplaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    industry_sector = Column(String(50), nullable=False, default="construction")
    address = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    fatigue_policy_id = Column(String(36), ForeignKey("fatigue_policies.id"), nullable=False)
    site_qr_secret = Column(String(100), nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    fatigue_policy = relationship("FatiguePolicy", back_populates="workplaces")
    shifts = relationship("Shift", back_populates="workplace")
    safety_reports = relationship("SafetyReport", back_populates="workplace")

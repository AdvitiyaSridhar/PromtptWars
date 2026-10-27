import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class FatiguePolicy(Base):
    __tablename__ = "fatigue_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    policy_name = Column(String(100), nullable=False)
    industry_sector = Column(String(50), index=True, nullable=False)  # "construction", "gig_platform"
    max_daily_hours = Column(Float, nullable=False, default=10.0)
    min_rest_hours_between_shifts = Column(Float, nullable=False, default=11.0)
    max_weekly_hours = Column(Float, nullable=False, default=50.0)
    mandatory_break_threshold_hours = Column(Float, nullable=False, default=4.5)
    mandatory_break_duration_minutes = Column(Float, nullable=False, default=30.0)
    max_consecutive_days = Column(Integer, nullable=False, default=6)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workplaces = relationship("Workplace", back_populates="fatigue_policy")

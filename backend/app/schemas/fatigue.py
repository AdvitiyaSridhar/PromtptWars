from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class FatiguePolicyCreate(BaseModel):
    policy_name: str
    industry_sector: str = Field(..., pattern="^(construction|gig_platform)$")
    max_daily_hours: float = Field(default=10.0, gt=0, le=24)
    min_rest_hours_between_shifts: float = Field(default=11.0, ge=0, le=24)
    max_weekly_hours: float = Field(default=50.0, gt=0, le=168)
    mandatory_break_threshold_hours: float = Field(default=4.5, gt=0)
    mandatory_break_duration_minutes: float = Field(default=30.0, ge=0)
    max_consecutive_days: int = Field(default=6, ge=1, le=14)

class FatiguePolicyUpdate(BaseModel):
    policy_name: Optional[str] = None
    max_daily_hours: Optional[float] = Field(default=None, gt=0, le=24)
    min_rest_hours_between_shifts: Optional[float] = Field(default=None, ge=0, le=24)
    max_weekly_hours: Optional[float] = Field(default=None, gt=0, le=168)
    mandatory_break_threshold_hours: Optional[float] = Field(default=None, gt=0)
    mandatory_break_duration_minutes: Optional[float] = Field(default=None, ge=0, le=1440)
    max_consecutive_days: Optional[int] = Field(default=None, ge=1, le=14)

class FatiguePolicyOut(BaseModel):
    id: str
    policy_name: str
    industry_sector: str
    max_daily_hours: float
    min_rest_hours_between_shifts: float
    max_weekly_hours: float
    mandatory_break_threshold_hours: float
    mandatory_break_duration_minutes: float
    max_consecutive_days: int
    updated_at: datetime

    class Config:
        from_attributes = True

class FatigueEligibilityOut(BaseModel):
    worker_id: str
    worker_name: str
    industry_sector: str
    policy_applied: str
    hours_worked_past_24h: float
    hours_worked_past_7d: float
    rest_hours_elapsed: float
    max_daily_hours: float
    min_rest_hours_between_shifts: float
    max_weekly_hours: float
    is_eligible: bool
    eligibility_status: str  # "ELIGIBLE" or "BLOCKED_FATIGUE"
    rejection_reason: Optional[str] = None

class FatigueExceptionLogOut(BaseModel):
    id: str
    worker_id: str
    worker_name: Optional[str] = None
    shift_id: Optional[str] = None
    workplace_id: str
    workplace_name: Optional[str] = None
    attempted_action: str
    timestamp: datetime
    breach_type: str
    hours_worked_past_24h: float
    rest_hours_elapsed: float
    policy_required_rest: float
    policy_max_daily: float
    rejection_reason: str
    reviewed_by_admin: bool
    admin_audit_notes: Optional[str] = None

    class Config:
        from_attributes = True

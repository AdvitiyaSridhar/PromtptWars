from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class ShiftCreate(BaseModel):
    worker_id: str
    workplace_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    base_hourly_rate: Decimal = Field(default=Decimal("25.00"), gt=Decimal("0.00"))
    overtime_rate_multiplier: Decimal = Field(default=Decimal("1.50"), ge=Decimal("1.00"))

    @model_validator(mode="after")
    def validate_shift_times(self):
        start = self.scheduled_start
        end = self.scheduled_end
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("Shift start and end must include a timezone.")
        duration_hours = (end - start).total_seconds() / 3600
        if duration_hours <= 0 or duration_hours > 24:
            raise ValueError("Shift duration must be greater than zero and no more than 24 hours.")
        return self

class WorkplaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    address: str = Field(..., min_length=2, max_length=255)
    industry_sector: str = Field(..., pattern="^(construction|gig_platform)$")
    fatigue_policy_id: str

class ShiftOut(BaseModel):
    id: str
    worker_id: str
    workplace_id: str
    workplace_name: Optional[str] = None
    worker_name: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    base_hourly_rate: Decimal
    overtime_rate_multiplier: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class QRCheckinRequest(BaseModel):
    scanned_site_token: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class QRCheckinResponse(BaseModel):
    success: bool
    status: str
    shift_id: str
    workplace_name: str
    actual_start: str
    physical_access_note: str

class CheckoutResponse(BaseModel):
    success: bool
    status: str
    shift_id: str
    actual_start: str
    actual_end: str
    duration_hours: float
    gross_pay: Decimal
    net_pay: Decimal

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List

class SafetyActionCreate(BaseModel):
    action_description: str = Field(..., min_length=5)
    assigned_to: str
    due_date: date

class SafetyActionResolve(BaseModel):
    verification_notes: str = Field(..., min_length=5)

class SafetyReportStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(investigating|closed)$")

class SafetyActionOut(BaseModel):
    id: str
    report_id: str
    action_description: str
    assigned_to: str
    assignee_name: Optional[str] = None
    due_date: date
    completed_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    verified_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SafetyReportCreate(BaseModel):
    workplace_id: str
    shift_id: Optional[str] = None
    category: str = Field(..., pattern="^(hazard|near_miss|injury|heat_stress|ppe_shortage|equipment_defect)$")
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    is_anonymous: bool = False

class SafetyReportOut(BaseModel):
    id: str
    reporter_id: Optional[str] = None  # None if is_anonymous when viewed by non-admin
    reporter_name: Optional[str] = None
    workplace_id: str
    workplace_name: Optional[str] = None
    shift_id: Optional[str] = None
    category: str
    severity: str
    title: str
    description: str
    is_anonymous: bool
    status: str
    assigned_to: Optional[str] = None
    assignee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    actions: List[SafetyActionOut] = []

    class Config:
        from_attributes = True

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal

class PayDisputeCreate(BaseModel):
    shift_id: str
    ledger_id: Optional[str] = None
    dispute_type: str = Field(..., pattern="^(unpaid_hours|unauthorized_deduction|wrong_rate|missing_break)$")
    claimed_amount: Decimal = Field(..., gt=Decimal("0.00"))
    worker_explanation: str = Field(..., min_length=10)

class PayDisputeReview(BaseModel):
    status: str = Field(..., pattern="^(under_review|evidence_requested|resolved_upheld|resolved_rejected)$")
    settled_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    resolution_notes: str = Field(..., min_length=5)

class PayDisputeOut(BaseModel):
    id: str
    worker_id: str
    worker_name: Optional[str] = None
    shift_id: str
    ledger_id: Optional[str] = None
    workplace_name: Optional[str] = None
    dispute_type: str
    claimed_amount: Decimal
    worker_explanation: str
    status: str
    settled_amount: Optional[Decimal] = None
    resolution_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewer_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

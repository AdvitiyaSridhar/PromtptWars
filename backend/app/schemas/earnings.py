from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class DeductionCreate(BaseModel):
    category: str = Field(..., pattern="^(equipment_rental|uniform|transport|advance|other)$")
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    description: str = Field(..., min_length=3)
    authorization_doc_ref: Optional[str] = None

class DeductionOut(BaseModel):
    id: str
    ledger_id: str
    category: str
    amount: Decimal
    description: str
    authorization_doc_ref: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class EarningsLedgerOut(BaseModel):
    id: str
    shift_id: str
    worker_id: str
    worker_name: Optional[str] = None
    workplace_name: Optional[str] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    regular_hours: Decimal
    overtime_hours: Decimal
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    currency: str
    payment_status: str
    paid_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    deductions: List[DeductionOut] = []

    class Config:
        from_attributes = True

class PaymentStatusUpdate(BaseModel):
    payment_status: str = Field(..., pattern="^(pending|approved|paid)$")
    payment_reference: Optional[str] = None

    @model_validator(mode="after")
    def require_reference_for_paid(self):
        if self.payment_status == "paid" and not self.payment_reference:
            raise ValueError("A payment reference is required when marking a ledger entry paid.")
        return self

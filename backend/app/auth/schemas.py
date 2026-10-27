from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class UserRegister(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.\+-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: str = Field(default="worker", pattern="^worker$")
    industry_sector: str = Field(default="construction", pattern="^(construction|gig_platform)$")
    phone_number: Optional[str] = None

class WorkerCreate(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.\+-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=10)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.\+-]+@[\w\.-]+\.\w+$")
    password: str

class UserOut(BaseModel):
    id: str
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    email: str
    full_name: str
    role: str
    industry_sector: str
    phone_number: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

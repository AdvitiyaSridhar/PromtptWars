import uuid
from sqlalchemy import Column, String
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    industry_sector = Column(String(50), nullable=False)

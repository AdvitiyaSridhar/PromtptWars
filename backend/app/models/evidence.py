import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base

class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_entity_type = Column(String(50), nullable=False)  # "safety_report", "pay_dispute", "corrective_action"
    parent_entity_id = Column(String(36), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])

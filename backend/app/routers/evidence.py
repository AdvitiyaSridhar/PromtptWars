import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.models.dispute import PayDispute
from app.models.evidence import EvidenceFile
from app.models.safety import SafetyReport
from app.models.shift import Shift
from app.models.user import User
from app.models.workplace import Workplace
from app.services.storage_service import get_storage_service

router = APIRouter(prefix="/evidence", tags=["Private Evidence"])


@router.get("/{evidence_id}")
def download_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    evidence = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    if evidence.parent_entity_type == "safety_report":
        parent = db.query(SafetyReport).join(Workplace).filter(
            SafetyReport.id == evidence.parent_entity_id,
            Workplace.organization_id == current_user.organization_id,
        ).first()
        owner_id = parent.reporter_id if parent else None
    elif evidence.parent_entity_type == "pay_dispute":
        parent = db.query(PayDispute).join(Shift).join(Workplace).filter(
            PayDispute.id == evidence.parent_entity_id,
            Workplace.organization_id == current_user.organization_id,
        ).first()
        owner_id = parent.worker_id if parent else None
    else:
        parent = None
        owner_id = None

    if not parent:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    if current_user.role == "worker" and owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this evidence.")
    if current_user.role not in ("worker", "employer_admin", "safety_officer"):
        raise HTTPException(status_code=403, detail="You are not allowed to access this evidence.")

    if evidence.storage_path.startswith("gs://"):
        signed_url = get_storage_service().get_url(evidence.storage_path)
        return RedirectResponse(signed_url, status_code=307)

    file_name = os.path.basename(evidence.storage_path)
    file_path = os.path.join(settings.LOCAL_UPLOAD_DIR, file_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Evidence file is unavailable.")
    return FileResponse(
        file_path,
        media_type=evidence.mime_type,
        filename=os.path.basename(evidence.file_name),
        content_disposition_type="attachment",
    )

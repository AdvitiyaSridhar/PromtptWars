import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.safety import SafetyReport, SafetyAction
from app.models.workplace import Workplace
from app.models.shift import Shift
from app.models.evidence import EvidenceFile
from app.schemas.safety import (
    SafetyReportCreate, SafetyReportOut, SafetyActionCreate, SafetyActionResolve, SafetyActionOut,
    SafetyReportStatusUpdate
)
from app.auth.dependencies import get_current_user, require_safety_officer_or_admin
from app.services.storage_service import get_storage_service

router = APIRouter(prefix="/safety", tags=["Safety Reporting & Corrective Actions"])

def serialize_report(report: SafetyReport, current_user: User) -> SafetyReportOut:
    is_admin = current_user.role in ["employer_admin", "safety_officer"]
    is_own = report.reporter_id == current_user.id

    # Anonymity protection: hide reporter if anonymous and user is not the reporter
    if report.is_anonymous and not is_own:
        reporter_id = None
        reporter_name = "Anonymous Worker (Identity Protected)"
    else:
        reporter_id = report.reporter_id
        reporter_name = report.reporter.full_name if report.reporter else "Reporter"

    actions = [
        SafetyActionOut(
            id=a.id,
            report_id=a.report_id,
            action_description=a.action_description,
            assigned_to=a.assigned_to,
            assignee_name=a.assignee.full_name if a.assignee else "Assignee",
            due_date=a.due_date,
            completed_at=a.completed_at,
            verification_notes=a.verification_notes,
            verified_by=a.verified_by,
            created_at=a.created_at
        ) for a in report.actions
    ]

    return SafetyReportOut(
        id=report.id,
        reporter_id=reporter_id,
        reporter_name=reporter_name,
        workplace_id=report.workplace_id,
        workplace_name=report.workplace.name if report.workplace else "Site",
        shift_id=report.shift_id,
        category=report.category,
        severity=report.severity,
        title=report.title,
        description=report.description,
        is_anonymous=report.is_anonymous,
        status=report.status,
        assigned_to=report.assigned_to,
        assignee_name=report.assignee.full_name if report.assignee else None,
        created_at=report.created_at,
        updated_at=report.updated_at,
        actions=actions
    )

@router.post("/reports", response_model=SafetyReportOut, status_code=status.HTTP_201_CREATED)
def submit_safety_report(
    report_in: SafetyReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workplace = db.query(Workplace).filter(
        Workplace.id == report_in.workplace_id,
        Workplace.organization_id == current_user.organization_id
    ).first()
    if not workplace:
        raise HTTPException(status_code=404, detail="Workplace not found in your organization.")
    if report_in.shift_id:
        shift = db.query(Shift).filter(
            Shift.id == report_in.shift_id,
            Shift.workplace_id == workplace.id,
            Shift.worker_id == current_user.id
        ).first()
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found for this worker and site.")
    report = SafetyReport(
        reporter_id=current_user.id,
        workplace_id=report_in.workplace_id,
        shift_id=report_in.shift_id,
        category=report_in.category,
        severity=report_in.severity,
        title=report_in.title,
        description=report_in.description,
        is_anonymous=report_in.is_anonymous,
        status="submitted"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return serialize_report(report, current_user)

@router.get("/reports", response_model=List[SafetyReportOut])
def list_safety_reports(
    workplace_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SafetyReport).join(Workplace).filter(
        Workplace.organization_id == current_user.organization_id
    )
    if workplace_id:
        query = query.filter(SafetyReport.workplace_id == workplace_id)

    if current_user.role == "worker":
        query = query.filter(SafetyReport.reporter_id == current_user.id)
    reports = query.order_by(SafetyReport.created_at.desc()).all()
    return [serialize_report(r, current_user) for r in reports]

@router.patch("/reports/{report_id}/status", response_model=SafetyReportOut)
def update_safety_report_status(
    report_id: str,
    update_in: SafetyReportStatusUpdate,
    db: Session = Depends(get_db),
    officer: User = Depends(require_safety_officer_or_admin)
):
    report = db.query(SafetyReport).join(Workplace).filter(
        SafetyReport.id == report_id,
        Workplace.organization_id == officer.organization_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Safety report not found.")
    report.status = update_in.status
    report.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return serialize_report(report, officer)

@router.post("/reports/{report_id}/actions", response_model=SafetyActionOut, status_code=status.HTTP_201_CREATED)
def add_corrective_action(
    report_id: str,
    action_in: SafetyActionCreate,
    db: Session = Depends(get_db),
    officer: User = Depends(require_safety_officer_or_admin)
):
    report = db.query(SafetyReport).join(Workplace).filter(
        SafetyReport.id == report_id,
        Workplace.organization_id == officer.organization_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Safety report not found.")
    assignee = db.query(User).filter(
        User.id == action_in.assigned_to,
        User.organization_id == officer.organization_id
    ).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found in your organization.")

    action = SafetyAction(
        report_id=report.id,
        action_description=action_in.action_description,
        assigned_to=action_in.assigned_to,
        due_date=action_in.due_date
    )
    db.add(action)

    report.status = "corrective_action_pending"
    report.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)

    return SafetyActionOut(
        id=action.id,
        report_id=action.report_id,
        action_description=action.action_description,
        assigned_to=action.assigned_to,
        assignee_name=action.assignee.full_name if action.assignee else "Assignee",
        due_date=action.due_date,
        completed_at=action.completed_at,
        verification_notes=action.verification_notes,
        verified_by=action.verified_by,
        created_at=action.created_at
    )

@router.patch("/actions/{action_id}/resolve", response_model=SafetyActionOut)
def resolve_corrective_action(
    action_id: str,
    resolve_in: SafetyActionResolve,
    db: Session = Depends(get_db),
    officer: User = Depends(require_safety_officer_or_admin)
):
    action = db.query(SafetyAction).join(SafetyReport).join(Workplace).filter(
        SafetyAction.id == action_id,
        Workplace.organization_id == officer.organization_id
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail="Corrective action not found.")

    now = datetime.now(timezone.utc)
    action.completed_at = now
    action.verification_notes = resolve_in.verification_notes
    action.verified_by = officer.id

    # Check if all actions on report are now complete
    report = action.report
    all_completed = all(a.completed_at is not None for a in report.actions)
    if all_completed:
        report.status = "resolved"
        report.updated_at = now

    db.commit()
    db.refresh(action)

    return SafetyActionOut(
        id=action.id,
        report_id=action.report_id,
        action_description=action.action_description,
        assigned_to=action.assigned_to,
        assignee_name=action.assignee.full_name if action.assignee else "Assignee",
        due_date=action.due_date,
        completed_at=action.completed_at,
        verification_notes=action.verification_notes,
        verified_by=officer.id,
        created_at=action.created_at
    )

@router.post("/reports/{report_id}/evidence")
async def upload_safety_evidence(
    report_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(SafetyReport).join(Workplace).filter(
        SafetyReport.id == report_id,
        Workplace.organization_id == current_user.organization_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Safety report not found.")
    if current_user.role == "worker" and report.reporter_id != current_user.id:
        raise HTTPException(status_code=403, detail="You may only upload evidence for your own report.")

    storage_service = get_storage_service()
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Evidence files must be 10 MB or smaller.")
    mime_type = file.content_type or "application/octet-stream"
    file_name = os.path.basename(file.filename or "evidence")[:255]
    storage_path = storage_service.save_file(file_name, content, mime_type)

    evidence = EvidenceFile(
        parent_entity_type="safety_report",
        parent_entity_id=report.id,
        file_name=file_name,
        storage_path=storage_path,
        mime_type=mime_type,
        file_size_bytes=len(content),
        uploaded_by=current_user.id
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return {
        "success": True,
        "evidence_id": evidence.id,
        "file_name": evidence.file_name,
        "url": f"/api/v1/evidence/{evidence.id}"
    }

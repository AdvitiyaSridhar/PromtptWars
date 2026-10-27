import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.shift import Shift
from app.models.earnings import EarningsLedger
from app.models.workplace import Workplace
from app.models.dispute import PayDispute
from app.models.evidence import EvidenceFile
from app.schemas.dispute import PayDisputeCreate, PayDisputeReview, PayDisputeOut
from app.auth.dependencies import get_current_user, require_admin, require_worker
from app.services.storage_service import get_storage_service
from app.services.earnings_calculator import EarningsCalculator

router = APIRouter(prefix="/disputes", tags=["Fair-Work Evidence & Resolution Tracker"])

def serialize_dispute(d: PayDispute) -> PayDisputeOut:
    return PayDisputeOut(
        id=d.id,
        worker_id=d.worker_id,
        worker_name=d.worker.full_name if d.worker else "Unknown",
        shift_id=d.shift_id,
        ledger_id=d.ledger_id,
        workplace_name=d.shift.workplace.name if d.shift and d.shift.workplace else "Site",
        dispute_type=d.dispute_type,
        claimed_amount=Decimal(str(d.claimed_amount)),
        worker_explanation=d.worker_explanation,
        status=d.status,
        settled_amount=Decimal(str(d.settled_amount)) if d.settled_amount is not None else None,
        resolution_notes=d.resolution_notes,
        reviewed_by=d.reviewed_by,
        reviewer_name=d.reviewer.full_name if d.reviewer else None,
        resolved_at=d.resolved_at,
        created_at=d.created_at
    )

@router.post("", response_model=PayDisputeOut, status_code=status.HTTP_201_CREATED)
def file_dispute(
    dispute_in: PayDisputeCreate,
    db: Session = Depends(get_db),
    worker: User = Depends(require_worker)
):
    shift = db.query(Shift).filter(Shift.id == dispute_in.shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift referenced in dispute not found.")

    if shift.worker_id != worker.id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot file a dispute against another worker's shift.")

    ledger = db.query(EarningsLedger).filter(EarningsLedger.shift_id == shift.id).first()
    if dispute_in.ledger_id and (not ledger or dispute_in.ledger_id != ledger.id):
        raise HTTPException(status_code=422, detail="The ledger entry must belong to the selected shift.")
    if dispute_in.claimed_amount < 0:
        raise HTTPException(status_code=422, detail="Claimed amount cannot be negative.")

    dispute = PayDispute(
        worker_id=worker.id,
        shift_id=shift.id,
        ledger_id=ledger.id if ledger else dispute_in.ledger_id,
        dispute_type=dispute_in.dispute_type,
        claimed_amount=EarningsCalculator.round_currency(dispute_in.claimed_amount),
        worker_explanation=dispute_in.worker_explanation,
        status="submitted"
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)

    return serialize_dispute(dispute)

@router.get("", response_model=List[PayDisputeOut])
def list_disputes(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(PayDispute).join(Shift).join(Workplace).filter(
        Workplace.organization_id == current_user.organization_id
    )

    # Insecure Direct Object Reference prevention: Workers can only view their own disputes
    if current_user.role == "worker":
        query = query.filter(PayDispute.worker_id == current_user.id)
    elif current_user.role != "employer_admin":
        raise HTTPException(status_code=403, detail="Only workers and organization administrators can review disputes.")
    
    if status_filter:
        query = query.filter(PayDispute.status == status_filter)

    disputes = query.order_by(PayDispute.created_at.desc()).all()
    return [serialize_dispute(d) for d in disputes]

@router.patch("/{dispute_id}/review", response_model=PayDisputeOut)
def review_dispute(
    dispute_id: str,
    review_in: PayDisputeReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    dispute = db.query(PayDispute).join(Shift).join(Workplace).filter(
        PayDispute.id == dispute_id,
        Workplace.organization_id == admin.organization_id
    ).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found.")
    if dispute.resolved_at is not None:
        raise HTTPException(status_code=409, detail="This dispute has already been resolved.")

    now = datetime.now(timezone.utc)
    dispute.status = review_in.status
    dispute.resolution_notes = review_in.resolution_notes
    dispute.reviewed_by = admin.id

    if review_in.status in ["resolved_upheld", "resolved_rejected"]:
        dispute.resolved_at = now

    # Automated Settlement: If upheld, adjust worker's ledger
    if review_in.status == "resolved_upheld":
        settled_amt = review_in.settled_amount if review_in.settled_amount is not None else dispute.claimed_amount
        if settled_amt < 0:
            raise HTTPException(status_code=422, detail="Settlement amount cannot be negative.")
        dispute.settled_amount = EarningsCalculator.round_currency(settled_amt)

        # If a ledger entry exists for this shift, adjust the net pay
        if dispute.ledger:
            ledger = dispute.ledger
            current_net = Decimal(str(ledger.net_pay))
            current_gross = Decimal(str(ledger.gross_pay))
            # Increase gross & net pay by the upheld settlement amount
            ledger.gross_pay = EarningsCalculator.round_currency(current_gross + settled_amt)
            ledger.net_pay = EarningsCalculator.round_currency(current_net + settled_amt)
            ledger.payment_reference = f"Adj: Dispute #{dispute.id[:8]} Upheld (+${settled_amt})"
            if ledger.payment_status == "paid":
                ledger.payment_status = "approved"
                ledger.paid_at = None

    db.commit()
    db.refresh(dispute)
    return serialize_dispute(dispute)

@router.post("/{dispute_id}/evidence")
async def upload_dispute_evidence(
    dispute_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dispute = db.query(PayDispute).join(Shift).join(Workplace).filter(
        PayDispute.id == dispute_id,
        Workplace.organization_id == current_user.organization_id
    ).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found.")

    # Permissions: Only the filing worker or an admin can upload evidence
    if current_user.role == "worker" and dispute.worker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot upload evidence for another worker's dispute.")

    storage_service = get_storage_service()
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Evidence files must be 10 MB or smaller.")
    mime_type = file.content_type or "application/octet-stream"
    file_name = os.path.basename(file.filename or "evidence")[:255]
    storage_path = storage_service.save_file(file_name, content, mime_type)

    evidence = EvidenceFile(
        parent_entity_type="pay_dispute",
        parent_entity_id=dispute.id,
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

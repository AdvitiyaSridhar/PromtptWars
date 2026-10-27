from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.earnings import EarningsLedger, Deduction
from app.models.shift import Shift
from app.models.workplace import Workplace
from app.schemas.earnings import (
    EarningsLedgerOut, DeductionCreate, DeductionOut, PaymentStatusUpdate
)
from app.auth.dependencies import get_current_user, require_admin, require_worker
from app.services.earnings_calculator import EarningsCalculator

router = APIRouter(prefix="/ledger", tags=["Work & Earnings Ledger"])

def serialize_ledger_entry(entry: EarningsLedger) -> EarningsLedgerOut:
    shift = entry.shift
    worker = entry.worker
    return EarningsLedgerOut(
        id=entry.id,
        shift_id=entry.shift_id,
        worker_id=entry.worker_id,
        worker_name=worker.full_name if worker else "Unknown",
        workplace_name=shift.workplace.name if shift and shift.workplace else "Site",
        shift_start=shift.actual_start or (shift.scheduled_start if shift else None),
        shift_end=shift.actual_end or (shift.scheduled_end if shift else None),
        regular_hours=Decimal(str(entry.regular_hours)),
        overtime_hours=Decimal(str(entry.overtime_hours)),
        gross_pay=Decimal(str(entry.gross_pay)),
        total_deductions=Decimal(str(entry.total_deductions)),
        net_pay=Decimal(str(entry.net_pay)),
        currency=entry.currency,
        payment_status=entry.payment_status,
        paid_at=entry.paid_at,
        payment_reference=entry.payment_reference,
        created_at=entry.created_at,
        deductions=[
            DeductionOut(
                id=d.id,
                ledger_id=d.ledger_id,
                category=d.category,
                amount=Decimal(str(d.amount)),
                description=d.description,
                authorization_doc_ref=d.authorization_doc_ref,
                created_at=d.created_at
            ) for d in entry.deductions
        ]
    )

@router.get("/worker", response_model=List[EarningsLedgerOut])
def get_worker_earnings(
    db: Session = Depends(get_db),
    worker: User = Depends(require_worker)
):
    entries = db.query(EarningsLedger).join(Shift).join(Workplace).filter(
        EarningsLedger.worker_id == worker.id,
        Workplace.organization_id == worker.organization_id
    ).order_by(EarningsLedger.created_at.desc()).all()
    return [serialize_ledger_entry(e) for e in entries]

@router.get("/admin", response_model=dict)
def get_admin_payroll_ledger(
    status_filter: Optional[str] = Query(None, alias="status"),
    worker_id: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(EarningsLedger).join(Shift).join(Workplace).filter(
        Workplace.organization_id == admin.organization_id
    )
    if status_filter:
        query = query.filter(EarningsLedger.payment_status == status_filter)
    if worker_id:
        query = query.filter(EarningsLedger.worker_id == worker_id)

    entries = query.order_by(EarningsLedger.created_at.desc()).all()
    serialized = [serialize_ledger_entry(e) for e in entries]

    # Calculate actual totals from stored records (not hardcoded dashboard numbers)
    total_gross = sum(Decimal(str(e.gross_pay)) for e in entries)
    total_deductions = sum(Decimal(str(e.total_deductions)) for e in entries)
    total_net = sum(Decimal(str(e.net_pay)) for e in entries)

    return {
        "entries": serialized,
        "summary": {
            "total_shifts_recorded": len(entries),
            "total_gross_pay": total_gross,
            "total_deductions": total_deductions,
            "total_net_pay": total_net,
            "currency": "USD",
            "arithmetic_invariant_verified": (total_gross - total_deductions == total_net)
        }
    }

@router.post("/{ledger_id}/deductions", response_model=DeductionOut, status_code=status.HTTP_201_CREATED)
def add_deduction_to_ledger(
    ledger_id: str,
    deduction_in: DeductionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    ledger = db.query(EarningsLedger).join(Shift).join(Workplace).filter(
        EarningsLedger.id == ledger_id,
        Workplace.organization_id == admin.organization_id
    ).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="Earnings ledger record not found.")

    if ledger.payment_status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add deductions to an already paid shift. File an administrative adjustment instead."
        )

    deduction = EarningsCalculator.add_deduction(
        db=db,
        ledger=ledger,
        category=deduction_in.category,
        amount=deduction_in.amount,
        description=deduction_in.description,
        authorization_doc_ref=deduction_in.authorization_doc_ref
    )

    return DeductionOut(
        id=deduction.id,
        ledger_id=deduction.ledger_id,
        category=deduction.category,
        amount=Decimal(str(deduction.amount)),
        description=deduction.description,
        authorization_doc_ref=deduction.authorization_doc_ref,
        created_at=deduction.created_at
    )

@router.patch("/{ledger_id}/status", response_model=EarningsLedgerOut)
def update_payment_status(
    ledger_id: str,
    update_in: PaymentStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    ledger = db.query(EarningsLedger).join(Shift).join(Workplace).filter(
        EarningsLedger.id == ledger_id,
        Workplace.organization_id == admin.organization_id
    ).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="Earnings ledger record not found.")

    next_statuses = {
        "pending": {"approved"},
        "approved": {"paid"},
        "paid": set(),
    }
    if update_in.payment_status not in next_statuses[ledger.payment_status]:
        raise HTTPException(status_code=409, detail="Payment status must move from pending to approved to paid and cannot be reversed.")
    if update_in.payment_status == "paid" and not update_in.payment_reference:
        raise HTTPException(status_code=422, detail="A payment reference is required when marking a ledger entry paid.")

    ledger.payment_status = update_in.payment_status
    if update_in.payment_status == "paid":
        ledger.paid_at = datetime.now(timezone.utc)
        if update_in.payment_reference:
            ledger.payment_reference = update_in.payment_reference

    db.commit()
    db.refresh(ledger)
    return serialize_ledger_entry(ledger)

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.workplace import Workplace
from app.models.fatigue_policy import FatiguePolicy
from app.auth.schemas import WorkerCreate
from app.auth.security import hash_password
from app.models.shift import Shift, CheckinEvent, AttendanceAttempt
from app.models.earnings import EarningsLedger
from app.schemas.shift import (
    ShiftCreate, ShiftOut, QRCheckinRequest, QRCheckinResponse, CheckoutResponse, WorkplaceCreate
)
from app.auth.dependencies import get_current_user, require_admin, require_worker
from app.services.fatigue_guard import FatigueGuardService
from app.services.qr_service import QRService
from app.services.earnings_calculator import EarningsCalculator

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

router = APIRouter(tags=["Shifts & QR Attendance"])

@router.get("/workplaces", response_model=List[dict])
def list_workplaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workplaces = db.query(Workplace).filter(Workplace.organization_id == current_user.organization_id).all()
    results = []
    for w in workplaces:
        qr_token = QRService.generate_site_qr_token(w)
        results.append({
            "id": w.id,
            "name": w.name,
            "industry_sector": w.industry_sector,
            "address": w.address,
            "latitude": w.latitude,
            "longitude": w.longitude,
            "site_qr_token": qr_token
        })
    return results

@router.post("/workplaces", status_code=status.HTTP_201_CREATED)
def create_workplace(
    workplace_in: WorkplaceCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if workplace_in.industry_sector != admin.industry_sector:
        raise HTTPException(status_code=422, detail="A work site must match your organization's industry.")
    policy = db.query(FatiguePolicy).filter(
        FatiguePolicy.id == workplace_in.fatigue_policy_id,
        FatiguePolicy.organization_id == admin.organization_id
    ).first()
    if not policy or policy.industry_sector != workplace_in.industry_sector:
        raise HTTPException(status_code=404, detail="A matching fatigue policy was not found in your organization.")
    workplace = Workplace(
        organization_id=admin.organization_id,
        name=workplace_in.name,
        address=workplace_in.address,
        industry_sector=workplace_in.industry_sector,
        fatigue_policy_id=policy.id
    )
    db.add(workplace)
    db.commit()
    db.refresh(workplace)
    return {
        "id": workplace.id,
        "name": workplace.name,
        "address": workplace.address,
        "industry_sector": workplace.industry_sector,
        "fatigue_policy_id": workplace.fatigue_policy_id
    }

@router.get("/workers")
def list_workers(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    workers = db.query(User).filter(
        User.organization_id == admin.organization_id,
        User.role == "worker",
        User.is_active.is_(True)
    ).order_by(User.full_name).all()
    return [{"id": user.id, "full_name": user.full_name, "email": user.email} for user in workers]

@router.post("/workers", status_code=status.HTTP_201_CREATED)
def create_worker(
    worker_in: WorkerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if db.query(User).filter(User.email == worker_in.email).first():
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    worker = User(
        organization_id=admin.organization_id,
        email=worker_in.email,
        hashed_password=hash_password(worker_in.password),
        full_name=worker_in.full_name,
        phone_number=worker_in.phone_number,
        role="worker",
        industry_sector=admin.industry_sector
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return {"id": worker.id, "email": worker.email, "full_name": worker.full_name, "role": worker.role}

@router.get("/workplaces/{workplace_id}/site-qr")
def get_site_qr_payload(
    workplace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    workplace = db.query(Workplace).filter(
        Workplace.id == workplace_id,
        Workplace.organization_id == current_user.organization_id
    ).first()
    if not workplace:
        raise HTTPException(status_code=404, detail="Workplace not found.")
    
    qr_token = QRService.generate_site_qr_token(workplace)
    return {
        "workplace_id": workplace.id,
        "workplace_name": workplace.name,
        "industry_sector": workplace.industry_sector,
        "site_qr_token": qr_token,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "This QR token identifies the work site. Scanning records worker attendance and verifies safety eligibility; it does not physically lock or grant physical entry."
    }

@router.get("/shifts", response_model=List[ShiftOut])
def list_shifts(
    status_filter: Optional[str] = Query(None, alias="status"),
    worker_id: Optional[str] = None,
    workplace_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Shift).join(Workplace).filter(
        Workplace.organization_id == current_user.organization_id
    )

    # Insecure Direct Object Reference prevention: Workers can only view their own shifts
    if current_user.role == "worker":
        query = query.filter(Shift.worker_id == current_user.id)
    else:
        if worker_id:
            query = query.filter(Shift.worker_id == worker_id)

    if workplace_id:
        query = query.filter(Shift.workplace_id == workplace_id)
    if status_filter:
        query = query.filter(Shift.status == status_filter)

    shifts = query.order_by(Shift.scheduled_start.desc()).all()
    results = []
    for s in shifts:
        out = ShiftOut(
            id=s.id,
            worker_id=s.worker_id,
            workplace_id=s.workplace_id,
            workplace_name=s.workplace.name if s.workplace else "Unknown Site",
            worker_name=s.worker.full_name if s.worker else "Unknown Worker",
            scheduled_start=s.scheduled_start,
            scheduled_end=s.scheduled_end,
            actual_start=s.actual_start,
            actual_end=s.actual_end,
            base_hourly_rate=Decimal(str(s.base_hourly_rate)),
            overtime_rate_multiplier=Decimal(str(s.overtime_rate_multiplier)),
            status=s.status,
            created_at=s.created_at
        )
        results.append(out)
    return results

@router.get("/shifts/attendance")
def list_attendance_events(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    events = db.query(CheckinEvent).join(Workplace).filter(
        Workplace.organization_id == admin.organization_id
    ).order_by(CheckinEvent.timestamp.desc()).limit(100).all()
    attempts = db.query(AttendanceAttempt).filter(
        AttendanceAttempt.organization_id == admin.organization_id
    ).order_by(AttendanceAttempt.timestamp.desc()).limit(100).all()
    rows = [
        {
            "id": event.id,
            "worker_name": event.shift.worker.full_name if event.shift and event.shift.worker else "Worker",
            "site_name": event.shift.workplace.name if event.shift and event.shift.workplace else "Work site",
            "shift_id": event.shift_id,
            "action": event.event_type,
            "timestamp": event.timestamp,
            "result": event.verification_status,
            "reason": event.details,
        }
        for event in events
    ]
    rows.extend({
        "id": attempt.id,
        "worker_name": attempt.worker.full_name if attempt.worker else "Worker",
        "site_name": (
            "Unverified QR site"
            if attempt.outcome_code in {"rejected_invalid_qr", "rejected_foreign_site"}
            else attempt.workplace.name if attempt.workplace else "Unknown site"
        ),
        "shift_id": attempt.shift_id,
        "action": attempt.attempted_action,
        "timestamp": attempt.timestamp,
        "result": attempt.outcome_code,
        "reason": attempt.reason,
    } for attempt in attempts)
    return sorted(rows, key=lambda row: row["timestamp"], reverse=True)[:100]

@router.post("/shifts", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def create_shift(
    shift_in: ShiftCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    scheduled_start = ensure_utc(shift_in.scheduled_start)
    if scheduled_start < datetime.now(timezone.utc) - timedelta(minutes=45):
        raise HTTPException(status_code=422, detail="A shift cannot be scheduled more than 45 minutes in the past.")
    # 1. Verify worker exists and is active
    worker = db.query(User).filter(
        User.id == shift_in.worker_id,
        User.role == "worker",
        User.organization_id == admin_user.organization_id
    ).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Target worker account not found.")

    # 2. Verify workplace exists
    workplace = db.query(Workplace).filter(
        Workplace.id == shift_in.workplace_id,
        Workplace.organization_id == admin_user.organization_id
    ).first()
    if not workplace:
        raise HTTPException(status_code=404, detail="Target workplace not found.")

    # 3. FatigueGuard Zero-Bypass Pre-Assignment Check
    # Will raise 422 FATIGUE_LIMIT_BREACHED if rest or daily limits are breached
    FatigueGuardService.validate_shift_assignment(
        db=db,
        worker_id=shift_in.worker_id,
        workplace_id=shift_in.workplace_id,
        scheduled_start=shift_in.scheduled_start,
        scheduled_end=shift_in.scheduled_end
    )

    # 4. Create Shift
    shift = Shift(
        worker_id=shift_in.worker_id,
        workplace_id=shift_in.workplace_id,
        created_by=admin_user.id,
        scheduled_start=shift_in.scheduled_start,
        scheduled_end=shift_in.scheduled_end,
        base_hourly_rate=shift_in.base_hourly_rate,
        overtime_rate_multiplier=shift_in.overtime_rate_multiplier,
        status="scheduled"
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    return ShiftOut(
        id=shift.id,
        worker_id=shift.worker_id,
        workplace_id=shift.workplace_id,
        workplace_name=workplace.name,
        worker_name=worker.full_name,
        scheduled_start=shift.scheduled_start,
        scheduled_end=shift.scheduled_end,
        actual_start=shift.actual_start,
        actual_end=shift.actual_end,
        base_hourly_rate=Decimal(str(shift.base_hourly_rate)),
        overtime_rate_multiplier=Decimal(str(shift.overtime_rate_multiplier)),
        status=shift.status,
        created_at=shift.created_at
    )

@router.get("/shifts/{shift_id}", response_model=ShiftOut)
def get_shift_detail(
    shift_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shift = db.query(Shift).join(Workplace).filter(
        Shift.id == shift_id,
        Workplace.organization_id == current_user.organization_id
    ).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found.")

    # Permission check
    if current_user.role == "worker" and shift.worker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot access another worker's shift records.")

    return ShiftOut(
        id=shift.id,
        worker_id=shift.worker_id,
        workplace_id=shift.workplace_id,
        workplace_name=shift.workplace.name if shift.workplace else "Unknown Site",
        worker_name=shift.worker.full_name if shift.worker else "Unknown Worker",
        scheduled_start=shift.scheduled_start,
        scheduled_end=shift.scheduled_end,
        actual_start=shift.actual_start,
        actual_end=shift.actual_end,
        base_hourly_rate=Decimal(str(shift.base_hourly_rate)),
        overtime_rate_multiplier=Decimal(str(shift.overtime_rate_multiplier)),
        status=shift.status,
        created_at=shift.created_at
    )

@router.post("/shifts/check-in", response_model=QRCheckinResponse)
def checkin_with_site_qr(
    req: QRCheckinRequest,
    db: Session = Depends(get_db),
    worker: User = Depends(require_worker)
):
    """Primary MVP QR Check-in Endpoint:
    Worker scans the Site QR code with their mobile device camera.
    Backend verifies token, resolves assigned shift, and validates zero-bypass FatigueGuard eligibility.
    """
    res = QRService.process_worker_checkin(
        db=db,
        worker_id=worker.id,
        organization_id=worker.organization_id,
        scanned_site_token=req.scanned_site_token,
        latitude=req.latitude,
        longitude=req.longitude
    )
    return QRCheckinResponse(**res)

@router.post("/shifts/{shift_id}/check-out", response_model=CheckoutResponse)
def checkout_shift(
    shift_id: str,
    req: Optional[QRCheckinRequest] = None,
    db: Session = Depends(get_db),
    worker: User = Depends(require_worker)
):
    """Records shift checkout, computes duration and overtime, and auto-generates ledger entry."""
    shift = db.query(Shift).join(Workplace).filter(
        Shift.id == shift_id,
        Workplace.organization_id == worker.organization_id
    ).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found.")

    if shift.worker_id != worker.id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot check out of another worker's shift.")

    if req:
        workplace = QRService.decode_and_verify_site_token(db, req.scanned_site_token)
        if workplace.id != shift.workplace_id or workplace.organization_id != worker.organization_id:
            raise HTTPException(status_code=403, detail="The scanned site does not match your active shift.")

    if shift.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check out: Shift status is '{shift.status}'. Only 'in_progress' shifts can be checked out."
        )

    now = datetime.now(timezone.utc)
    shift.actual_end = now
    shift.status = "completed"

    # Calculate Earnings & Ledger entry
    actual_start = shift.actual_start or shift.scheduled_start
    ledger = EarningsCalculator.calculate_shift_earnings(
        db=db,
        shift=shift,
        actual_start=actual_start,
        actual_end=now
    )

    # Log Checkout Event
    event = CheckinEvent(
        shift_id=shift.id,
        worker_id=worker.id,
        workplace_id=shift.workplace_id,
        event_type="check_out",
        timestamp=now,
        verification_status="verified",
        scanned_site_token=req.scanned_site_token[:32] + "..." if req else None,
        details="Worker checked out successfully"
    )
    event.recorded_latitude = req.latitude if req else None
    event.recorded_longitude = req.longitude if req else None
    db.add(event)
    db.commit()
    db.refresh(shift)

    start_utc = ensure_utc(actual_start)
    duration_hours = (now - start_utc).total_seconds() / 3600.0

    return CheckoutResponse(
        success=True,
        status="completed",
        shift_id=shift.id,
        actual_start=start_utc.isoformat(),
        actual_end=now.isoformat(),
        duration_hours=round(duration_hours, 2),
        gross_pay=Decimal(str(ledger.gross_pay)),
        net_pay=Decimal(str(ledger.net_pay))
    )

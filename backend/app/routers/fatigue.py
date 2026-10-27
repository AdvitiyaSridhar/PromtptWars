from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.fatigue_policy import FatiguePolicy
from app.models.workplace import Workplace
from app.models.shift import FatigueExceptionLog
from app.schemas.fatigue import (
    FatiguePolicyCreate, FatiguePolicyUpdate, FatiguePolicyOut,
    FatigueEligibilityOut, FatigueExceptionLogOut
)
from app.auth.dependencies import get_current_user, require_admin, require_safety_officer_or_admin
from app.services.fatigue_guard import FatigueGuardService

router = APIRouter(prefix="/fatigue", tags=["FatigueGuard & Safety Policies"])

@router.get("/policies", response_model=List[FatiguePolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    policies = db.query(FatiguePolicy).filter(
        FatiguePolicy.organization_id == current_user.organization_id
    ).all()
    return policies

@router.post("/policies", response_model=FatiguePolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_in: FatiguePolicyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if policy_in.industry_sector != admin.industry_sector:
        raise HTTPException(status_code=422, detail="A policy must match your organization's industry.")
    policy = FatiguePolicy(
        organization_id=admin.organization_id,
        **policy_in.model_dump()
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy

@router.put("/policies/{policy_id}", response_model=FatiguePolicyOut)
def update_policy(
    policy_id: str,
    update_in: FatiguePolicyUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    policy = db.query(FatiguePolicy).filter(
        FatiguePolicy.id == policy_id,
        FatiguePolicy.organization_id == admin.organization_id
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Fatigue policy not found.")

    update_data = update_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(policy, field, val)

    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)
    return policy

@router.get("/eligibility/{worker_id}", response_model=FatigueEligibilityOut)
def get_worker_fatigue_eligibility(
    worker_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # IDOR check: Workers can only check their own eligibility
    if current_user.role == "worker" and worker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot view another worker's fatigue metrics.")

    worker = db.query(User).filter(
        User.id == worker_id,
        User.organization_id == current_user.organization_id
    ).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found.")

    # Find applicable policy
    policy = db.query(FatiguePolicy).filter(
        FatiguePolicy.organization_id == worker.organization_id,
        FatiguePolicy.industry_sector == worker.industry_sector
    ).first()
    if not policy:
        raise HTTPException(status_code=409, detail="No fatigue policy is configured for this organization.")
    now = datetime.now(timezone.utc)
    metrics = FatigueGuardService.calculate_rolling_metrics(db, worker.id, now)

    # Check eligibility against baseline
    is_rest_breached = metrics["rest_hours_elapsed"] < policy.min_rest_hours_between_shifts
    is_daily_breached = metrics["hours_worked_past_24h"] >= policy.max_daily_hours
    is_weekly_breached = metrics["hours_worked_past_7d"] >= policy.max_weekly_hours

    is_eligible = not (is_rest_breached or is_daily_breached or is_weekly_breached)
    rejection_reason = None
    if is_rest_breached:
        rejection_reason = f"Rest required: {policy.min_rest_hours_between_shifts}h (currently {metrics['rest_hours_elapsed']}h elapsed)."
    elif is_daily_breached:
        rejection_reason = f"Daily cap reached: Worked {metrics['hours_worked_past_24h']}h in past 24h (limit {policy.max_daily_hours}h)."
    elif is_weekly_breached:
        rejection_reason = f"Weekly cap reached: Worked {metrics['hours_worked_past_7d']}h in 7 days (limit {policy.max_weekly_hours}h)."

    return FatigueEligibilityOut(
        worker_id=worker.id,
        worker_name=worker.full_name,
        industry_sector=worker.industry_sector,
        policy_applied=policy.policy_name,
        hours_worked_past_24h=metrics["hours_worked_past_24h"],
        hours_worked_past_7d=metrics["hours_worked_past_7d"],
        rest_hours_elapsed=metrics["rest_hours_elapsed"],
        max_daily_hours=policy.max_daily_hours,
        min_rest_hours_between_shifts=policy.min_rest_hours_between_shifts,
        max_weekly_hours=policy.max_weekly_hours,
        is_eligible=is_eligible,
        eligibility_status="ELIGIBLE" if is_eligible else "BLOCKED_FATIGUE",
        rejection_reason=rejection_reason
    )

@router.get("/exceptions", response_model=List[FatigueExceptionLogOut])
def list_fatigue_exceptions(
    db: Session = Depends(get_db),
    admin: User = Depends(require_safety_officer_or_admin)
):
    """Admin-only audit view: Attempted Exceptions & Fatigue Violations Log."""
    logs = db.query(FatigueExceptionLog).join(Workplace).filter(
        Workplace.organization_id == admin.organization_id
    ).order_by(FatigueExceptionLog.timestamp.desc()).all()
    results = []
    for log in logs:
        results.append(FatigueExceptionLogOut(
            id=log.id,
            worker_id=log.worker_id,
            worker_name=log.worker.full_name if log.worker else "Unknown",
            shift_id=log.shift_id,
            workplace_id=log.workplace_id,
            workplace_name=log.workplace.name if log.workplace else "Unknown",
            attempted_action=log.attempted_action,
            timestamp=log.timestamp,
            breach_type=log.breach_type,
            hours_worked_past_24h=log.hours_worked_past_24h,
            rest_hours_elapsed=log.rest_hours_elapsed,
            policy_required_rest=log.policy_required_rest,
            policy_max_daily=log.policy_max_daily,
            rejection_reason=log.rejection_reason,
            reviewed_by_admin=log.reviewed_by_admin,
            admin_audit_notes=log.admin_audit_notes
        ))
    return results

@router.patch("/exceptions/{log_id}/review", response_model=FatigueExceptionLogOut)
def review_fatigue_exception(
    log_id: str,
    notes: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Allows administrators to record audit notes on an attempted exception without bypassing the safety block."""
    log = db.query(FatigueExceptionLog).join(Workplace).filter(
        FatigueExceptionLog.id == log_id,
        Workplace.organization_id == admin.organization_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Exception log entry not found.")

    log.reviewed_by_admin = True
    log.admin_audit_notes = notes.get("admin_audit_notes", "Reviewed by administrator.")
    db.commit()
    db.refresh(log)

    return FatigueExceptionLogOut(
        id=log.id,
        worker_id=log.worker_id,
        worker_name=log.worker.full_name if log.worker else "Unknown",
        shift_id=log.shift_id,
        workplace_id=log.workplace_id,
        workplace_name=log.workplace.name if log.workplace else "Unknown",
        attempted_action=log.attempted_action,
        timestamp=log.timestamp,
        breach_type=log.breach_type,
        hours_worked_past_24h=log.hours_worked_past_24h,
        rest_hours_elapsed=log.rest_hours_elapsed,
        policy_required_rest=log.policy_required_rest,
        policy_max_daily=log.policy_max_daily,
        rejection_reason=log.rejection_reason,
        reviewed_by_admin=log.reviewed_by_admin,
        admin_audit_notes=log.admin_audit_notes
    )

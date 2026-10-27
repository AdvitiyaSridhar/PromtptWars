from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Tuple, Dict, Any, Optional
from fastapi import HTTPException, status
from app.models.shift import Shift, FatigueExceptionLog
from app.models.fatigue_policy import FatiguePolicy
from app.models.workplace import Workplace

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class FatigueGuardService:
    @staticmethod
    def get_policy_for_workplace(db: Session, workplace_id: str) -> FatiguePolicy:
        workplace = db.query(Workplace).filter(Workplace.id == workplace_id).first()
        if not workplace:
            raise HTTPException(status_code=404, detail="Workplace not found")
        policy = db.query(FatiguePolicy).filter(FatiguePolicy.id == workplace.fatigue_policy_id).first()
        if not policy:
            # Fallback to industry sector default policy
            policy = db.query(FatiguePolicy).filter(
                FatiguePolicy.organization_id == workplace.organization_id,
                FatiguePolicy.industry_sector == workplace.industry_sector
            ).first()
        if not policy:
            raise HTTPException(status_code=409, detail="No fatigue policy is configured for this workplace.")
        return policy

    @staticmethod
    def calculate_rolling_metrics(
        db: Session,
        worker_id: str,
        target_time: datetime,
        exclude_shift_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates hours worked in the rolling 24h, rolling 7d, and rest since last completed shift."""
        target_time = ensure_utc(target_time)
        # Rolling 24 hours window: [target_time - 24h, target_time]
        window_24h_start = target_time - timedelta(hours=24)
        window_7d_start = target_time - timedelta(days=7)

        # Count only work already elapsed at target_time, including accepted earlier schedules.
        shifts_7d = db.query(Shift).filter(
            Shift.worker_id == worker_id,
            Shift.status.in_(["scheduled", "completed", "in_progress"]),
            Shift.scheduled_start <= target_time,
            Shift.scheduled_end > window_7d_start
        )
        if exclude_shift_id:
            shifts_7d = shifts_7d.filter(Shift.id != exclude_shift_id)
        shifts_7d = shifts_7d.order_by(Shift.scheduled_end.desc()).all()

        hours_24h = 0.0
        hours_7d = 0.0

        for s in shifts_7d:
            s_start = ensure_utc(s.actual_start or s.scheduled_start)
            if s.status == "in_progress":
                s_end = min(target_time, ensure_utc(s.scheduled_end))
            else:
                s_end = ensure_utc(s.actual_end or s.scheduled_end)
                s_end = min(s_end, target_time)
            if not s_start or not s_end or s_end <= s_start:
                continue

            week_overlap_start = max(s_start, window_7d_start)
            week_overlap_end = min(s_end, target_time)
            if week_overlap_end > week_overlap_start:
                hours_7d += (week_overlap_end - week_overlap_start).total_seconds() / 3600.0

            # Overlap with the 24h window
            overlap_start = max(s_start, window_24h_start)
            overlap_end = min(s_end, target_time)
            if overlap_end > overlap_start:
                hours_24h += (overlap_end - overlap_start).total_seconds() / 3600.0

        prior_shifts = db.query(Shift).filter(
            Shift.worker_id == worker_id,
            Shift.status.in_(["scheduled", "completed"]),
            Shift.scheduled_end <= target_time
        ).all()
        prior_shift = max(
            prior_shifts,
            key=lambda shift: ensure_utc(shift.actual_end or shift.scheduled_end),
            default=None,
        )

        rest_hours_elapsed = None
        if prior_shift:
            prior_end = ensure_utc(prior_shift.actual_end or prior_shift.scheduled_end)
            if prior_end:
                rest_hours_elapsed = max(0.0, (target_time - prior_end).total_seconds() / 3600.0)
        else:
            rest_hours_elapsed = 999.0  # No prior shift, fully rested

        return {
            "hours_worked_past_24h": round(hours_24h, 2),
            "hours_worked_past_7d": round(hours_7d, 2),
            "rest_hours_elapsed": round(rest_hours_elapsed, 2) if rest_hours_elapsed is not None else 999.0,
            "last_shift_end": prior_shift.scheduled_end if prior_shift else None
        }

    @staticmethod
    def validate_shift_assignment(
        db: Session,
        worker_id: str,
        workplace_id: str,
        scheduled_start: datetime,
        scheduled_end: datetime,
        exclude_shift_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validates that a shift assignment does not violate work/rest limits or overlap existing shifts."""
        scheduled_start = ensure_utc(scheduled_start)
        scheduled_end = ensure_utc(scheduled_end)
        if scheduled_end <= scheduled_start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Shift end time must be after start time."
            )

        shift_duration = (scheduled_end - scheduled_start).total_seconds() / 3600.0
        policy = FatigueGuardService.get_policy_for_workplace(db, workplace_id)

        # 1. Check for overlapping shifts
        overlap_query = db.query(Shift).filter(
            Shift.worker_id == worker_id,
            Shift.status.in_(["scheduled", "in_progress"]),
            Shift.scheduled_start < scheduled_end,
            Shift.scheduled_end > scheduled_start
        )
        if exclude_shift_id:
            overlap_query = overlap_query.filter(Shift.id != exclude_shift_id)
        
        overlapping_shift = overlap_query.first()
        if overlapping_shift:
            rejection_reason = (
                f"Shift overlaps with existing shift {overlapping_shift.id} "
                f"({overlapping_shift.scheduled_start.strftime('%Y-%m-%d %H:%M')} to "
                f"{overlapping_shift.scheduled_end.strftime('%H:%M')})."
            )
            # Log exception
            log = FatigueExceptionLog(
                worker_id=worker_id,
                shift_id=None,
                workplace_id=workplace_id,
                attempted_action="shift_assignment",
                breach_type="overlapping_shifts",
                hours_worked_past_24h=0.0,
                rest_hours_elapsed=0.0,
                policy_required_rest=policy.min_rest_hours_between_shifts,
                policy_max_daily=policy.max_daily_hours,
                rejection_reason=rejection_reason
            )
            db.add(log)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "FATIGUE_LIMIT_BREACHED",
                    "breach_type": "overlapping_shifts",
                    "reason": rejection_reason,
                    "policy_applied": policy.policy_name
                }
            )

        # 2. Check Rest Gap from immediately preceding shift
        preceding_shift = db.query(Shift).filter(
            Shift.worker_id == worker_id,
            Shift.status.in_(["scheduled", "completed", "in_progress"]),
            Shift.scheduled_end <= scheduled_start
        ).order_by(Shift.scheduled_end.desc()).first()

        if preceding_shift:
            p_end = ensure_utc(preceding_shift.actual_end or preceding_shift.scheduled_end)
            rest_gap = (scheduled_start - p_end).total_seconds() / 3600.0
            if rest_gap < policy.min_rest_hours_between_shifts:
                rejection_reason = (
                    f"Insufficient rest: Only {round(rest_gap, 1)}h rest between shifts. "
                    f"Workplace policy '{policy.policy_name}' requires minimum {policy.min_rest_hours_between_shifts}h rest."
                )
                log = FatigueExceptionLog(
                    worker_id=worker_id,
                    shift_id=None,
                    workplace_id=workplace_id,
                    attempted_action="shift_assignment",
                    breach_type="insufficient_rest",
                    hours_worked_past_24h=0.0,
                    rest_hours_elapsed=round(rest_gap, 2),
                    policy_required_rest=policy.min_rest_hours_between_shifts,
                    policy_max_daily=policy.max_daily_hours,
                    rejection_reason=rejection_reason
                )
                db.add(log)
                db.commit()

                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "FATIGUE_LIMIT_BREACHED",
                        "breach_type": "insufficient_rest",
                        "reason": rejection_reason,
                        "rest_gap_hours": round(rest_gap, 2),
                        "required_rest_hours": policy.min_rest_hours_between_shifts,
                        "policy_applied": policy.policy_name
                    }
                )

        # 3. Check Projected Rolling 24h Hours
        metrics = FatigueGuardService.calculate_rolling_metrics(db, worker_id, scheduled_start)
        projected_24h = metrics["hours_worked_past_24h"] + shift_duration
        if projected_24h > policy.max_daily_hours:
            rejection_reason = (
                f"Daily limit exceeded: Projected {round(projected_24h, 1)}h in rolling 24-hour window exceeds "
                f"maximum limit of {policy.max_daily_hours}h under '{policy.policy_name}'."
            )
            log = FatigueExceptionLog(
                worker_id=worker_id,
                shift_id=None,
                workplace_id=workplace_id,
                attempted_action="shift_assignment",
                breach_type="daily_hours_exceeded",
                hours_worked_past_24h=metrics["hours_worked_past_24h"],
                rest_hours_elapsed=metrics["rest_hours_elapsed"],
                policy_required_rest=policy.min_rest_hours_between_shifts,
                policy_max_daily=policy.max_daily_hours,
                rejection_reason=rejection_reason
            )
            db.add(log)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "FATIGUE_LIMIT_BREACHED",
                    "breach_type": "daily_hours_exceeded",
                    "reason": rejection_reason,
                    "projected_hours": round(projected_24h, 2),
                    "max_daily_hours": policy.max_daily_hours,
                    "policy_applied": policy.policy_name
                }
            )

        # 4. Check Rolling 7d Weekly Hours
        projected_7d = metrics["hours_worked_past_7d"] + shift_duration
        if projected_7d > policy.max_weekly_hours:
            rejection_reason = (
                f"Weekly limit exceeded: Projected {round(projected_7d, 1)}h in 7 days exceeds "
                f"maximum limit of {policy.max_weekly_hours}h under '{policy.policy_name}'."
            )
            log = FatigueExceptionLog(
                worker_id=worker_id,
                shift_id=None,
                workplace_id=workplace_id,
                attempted_action="shift_assignment",
                breach_type="weekly_hours_exceeded",
                hours_worked_past_24h=metrics["hours_worked_past_24h"],
                rest_hours_elapsed=metrics["rest_hours_elapsed"],
                policy_required_rest=policy.min_rest_hours_between_shifts,
                policy_max_daily=policy.max_daily_hours,
                rejection_reason=rejection_reason
            )
            db.add(log)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "FATIGUE_LIMIT_BREACHED",
                    "breach_type": "weekly_hours_exceeded",
                    "reason": rejection_reason,
                    "projected_hours": round(projected_7d, 2),
                    "max_weekly_hours": policy.max_weekly_hours,
                    "policy_applied": policy.policy_name
                }
            )

        return {
            "eligible": True,
            "metrics": metrics,
            "policy": policy.policy_name
        }

    @staticmethod
    def validate_qr_checkin(
        db: Session,
        shift: Shift,
        checkin_time: datetime
    ) -> Dict[str, Any]:
        """Validates worker eligibility at the exact moment of QR check-in."""
        checkin_time = ensure_utc(checkin_time)
        policy = FatigueGuardService.get_policy_for_workplace(db, shift.workplace_id)
        metrics = FatigueGuardService.calculate_rolling_metrics(
            db, shift.worker_id, checkin_time, exclude_shift_id=shift.id
        )

        # 1. Enforce minimum rest since last completed shift
        if metrics["rest_hours_elapsed"] < policy.min_rest_hours_between_shifts:
            remaining_rest = round(policy.min_rest_hours_between_shifts - metrics["rest_hours_elapsed"], 1)
            rejection_reason = (
                f"Check-in blocked by FatigueGuard: Only {metrics['rest_hours_elapsed']}h rest elapsed since last shift. "
                f"Required rest is {policy.min_rest_hours_between_shifts}h. Worker needs {remaining_rest}h more rest."
            )
            log = FatigueExceptionLog(
                worker_id=shift.worker_id,
                shift_id=shift.id,
                workplace_id=shift.workplace_id,
                attempted_action="qr_check_in",
                breach_type="insufficient_rest",
                hours_worked_past_24h=metrics["hours_worked_past_24h"],
                rest_hours_elapsed=metrics["rest_hours_elapsed"],
                policy_required_rest=policy.min_rest_hours_between_shifts,
                policy_max_daily=policy.max_daily_hours,
                rejection_reason=rejection_reason
            )
            db.add(log)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "ELIGIBILITY_BLOCKED_FATIGUE",
                    "breach_type": "insufficient_rest",
                    "reason": rejection_reason,
                    "rest_hours_elapsed": metrics["rest_hours_elapsed"],
                    "required_rest_hours": policy.min_rest_hours_between_shifts,
                    "remaining_rest_needed_hours": remaining_rest,
                    "policy_applied": policy.policy_name
                }
            )

        # 2. Enforce rolling 24h work limit
        shift_duration = (ensure_utc(shift.scheduled_end) - ensure_utc(shift.scheduled_start)).total_seconds() / 3600.0
        if metrics["hours_worked_past_24h"] + shift_duration > policy.max_daily_hours:
            rejection_reason = (
                f"Check-in blocked by FatigueGuard: Worker has already worked {metrics['hours_worked_past_24h']}h in past 24h. "
                f"Adding this {round(shift_duration, 1)}h shift exceeds the {policy.max_daily_hours}h daily threshold."
            )
            log = FatigueExceptionLog(
                worker_id=shift.worker_id,
                shift_id=shift.id,
                workplace_id=shift.workplace_id,
                attempted_action="qr_check_in",
                breach_type="daily_hours_exceeded",
                hours_worked_past_24h=metrics["hours_worked_past_24h"],
                rest_hours_elapsed=metrics["rest_hours_elapsed"],
                policy_required_rest=policy.min_rest_hours_between_shifts,
                policy_max_daily=policy.max_daily_hours,
                rejection_reason=rejection_reason
            )
            db.add(log)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "ELIGIBILITY_BLOCKED_FATIGUE",
                    "breach_type": "daily_hours_exceeded",
                    "reason": rejection_reason,
                    "hours_worked_past_24h": metrics["hours_worked_past_24h"],
                    "max_daily_hours": policy.max_daily_hours,
                    "policy_applied": policy.policy_name
                }
            )

        if metrics["hours_worked_past_7d"] + shift_duration > policy.max_weekly_hours:
            rejection_reason = (
                f"Check-in blocked by FatigueGuard: The shift would exceed the "
                f"{policy.max_weekly_hours}h rolling 7-day threshold."
            )
            db.add(FatigueExceptionLog(
                worker_id=shift.worker_id,
                shift_id=shift.id,
                workplace_id=shift.workplace_id,
                attempted_action="qr_check_in",
                breach_type="weekly_hours_exceeded",
                hours_worked_past_24h=metrics["hours_worked_past_24h"],
                rest_hours_elapsed=metrics["rest_hours_elapsed"],
                policy_required_rest=policy.min_rest_hours_between_shifts,
                policy_max_daily=policy.max_daily_hours,
                rejection_reason=rejection_reason
            ))
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "ELIGIBILITY_BLOCKED_FATIGUE",
                    "breach_type": "weekly_hours_exceeded",
                    "reason": rejection_reason,
                    "hours_worked_past_7d": metrics["hours_worked_past_7d"],
                    "max_weekly_hours": policy.max_weekly_hours,
                    "policy_applied": policy.policy_name
                }
            )

        return {
            "eligible": True,
            "metrics": metrics,
            "policy": policy.policy_name
        }

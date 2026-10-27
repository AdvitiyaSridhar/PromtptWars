import json
from datetime import datetime, timezone, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Dict, Any, Optional

from app.config import settings
from app.models.workplace import Workplace
from app.models.shift import Shift, CheckinEvent, AttendanceAttempt
from app.services.fatigue_guard import FatigueGuardService

class QRService:
    @staticmethod
    def get_serializer() -> URLSafeTimedSerializer:
        return URLSafeTimedSerializer(settings.SITE_QR_SECRET, salt="fairshift-site-qr")

    @staticmethod
    def generate_site_qr_token(workplace: Workplace) -> str:
        serializer = QRService.get_serializer()
        payload = {
            "workplace_id": workplace.id,
            "site_name": workplace.name,
            "industry": workplace.industry_sector,
            "secret_hash": workplace.site_qr_secret[:8]
        }
        return serializer.dumps(payload)

    @staticmethod
    def decode_and_verify_site_token(db: Session, token: str) -> Workplace:
        serializer = QRService.get_serializer()
        try:
            # Valid for up to 30 days
            payload = serializer.loads(token, max_age=86400 * 30)
        except SignatureExpired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The scanned Site QR code has expired. Please refresh the workplace display."
            )
        except BadSignature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, corrupted, or tampered Site QR code."
            )

        workplace_id = payload.get("workplace_id")
        if not workplace_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed QR payload.")

        workplace = db.query(Workplace).filter(Workplace.id == workplace_id).first()
        if not workplace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workplace referenced by QR not found.")

        # Verify workplace secret hasn't been rotated
        if payload.get("secret_hash") != workplace.site_qr_secret[:8]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site QR code has been rotated or invalidated.")

        return workplace

    @staticmethod
    def process_worker_checkin(
        db: Session,
        worker_id: str,
        organization_id: Optional[str],
        scanned_site_token: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        checkin_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Core QR Check-In Workflow:
        1. Decode and verify site token.
        2. Find matching scheduled shift for worker at this workplace within time window.
        3. Enforce FatigueGuard eligibility (zero-bypass).
        4. Record CheckinEvent and update shift to in_progress.
        """
        if checkin_time is None:
            checkin_time = datetime.now(timezone.utc)

        # 1. Verify Site Token
        try:
            workplace = QRService.decode_and_verify_site_token(db, scanned_site_token)
        except HTTPException as error:
            audit_site = db.query(Workplace).filter(
                Workplace.organization_id == organization_id
            ).order_by(Workplace.id).first()
            if audit_site:
                db.add(AttendanceAttempt(
                    organization_id=organization_id,
                    worker_id=worker_id,
                    workplace_id=audit_site.id,
                    attempted_action="check_in",
                    timestamp=checkin_time,
                    outcome_code="rejected_invalid_qr",
                    reason=str(error.detail)
                ))
                db.commit()
            raise
        if workplace.organization_id != organization_id:
            audit_site = db.query(Workplace).filter(
                Workplace.organization_id == organization_id
            ).order_by(Workplace.id).first()
            if audit_site:
                db.add(AttendanceAttempt(
                    organization_id=organization_id,
                    worker_id=worker_id,
                    workplace_id=audit_site.id,
                    attempted_action="check_in",
                    timestamp=checkin_time,
                    outcome_code="rejected_foreign_site",
                    reason="The scanned site does not belong to the worker's organization."
                ))
                db.commit()
            raise HTTPException(status_code=404, detail="Workplace not found.")

        def record_rejection(status_code: str, reason: str, shift_id: Optional[str] = None) -> None:
            db.add(AttendanceAttempt(
                organization_id=organization_id,
                shift_id=shift_id,
                worker_id=worker_id,
                workplace_id=workplace.id,
                timestamp=checkin_time,
                attempted_action="check_in",
                outcome_code=status_code,
                reason=reason
            ))
            db.commit()

        # 2. Check for duplicate or active shifts
        active_shift = db.query(Shift).filter(
            Shift.worker_id == worker_id,
            Shift.status == "in_progress"
        ).first()

        if active_shift:
            record_rejection("rejected_duplicate", "Duplicate scan while a shift is active.")
            # Check if this is a double scan for the same shift
            if active_shift.workplace_id == workplace.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ALREADY_CHECKED_IN",
                        "shift_id": active_shift.id,
                        "message": "You are already checked in to an active shift at this site."
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "ACTIVE_SHIFT_EXISTS",
                        "shift_id": active_shift.id,
                        "message": "You currently have an active shift in progress at another site. Please check out first."
                    }
                )

        # 3. Locate scheduled shift within window
        # Window: [scheduled_start - 45 min, scheduled_end + 30 min]
        window_earliest = checkin_time - timedelta(minutes=45)
        window_latest = checkin_time + timedelta(minutes=45)

        # Look for shifts scheduled around this time
        candidate_shifts = db.query(Shift).filter(
            Shift.worker_id == worker_id,
            Shift.workplace_id == workplace.id,
            Shift.status == "scheduled",
            Shift.scheduled_start <= window_latest,
            Shift.scheduled_end >= checkin_time - timedelta(minutes=30)
        ).order_by(Shift.scheduled_start.asc()).all()

        if not candidate_shifts:
            # Check if there is any shift scheduled today to give a helpful rejection
            other_shift = db.query(Shift).filter(
                Shift.worker_id == worker_id,
                Shift.workplace_id == workplace.id,
                Shift.status == "scheduled"
            ).order_by(Shift.scheduled_start.asc()).first()

            if other_shift:
                reason = "Check-in attempted outside the assigned shift attendance window."
                record_rejection("rejected_window", reason, other_shift.id)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "SCHEDULE_WINDOW_INVALID",
                        "message": f"Check-in window invalid. Your shift is scheduled for {other_shift.scheduled_start.strftime('%Y-%m-%d %H:%M')}. Check-in opens 45 minutes prior.",
                        "scheduled_start": other_shift.scheduled_start.isoformat(),
                        "shift_id": other_shift.id
                    }
                )
            else:
                record_rejection("rejected_site", "No shift is assigned to this worker at the scanned site.")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "NO_SCHEDULED_SHIFT",
                        "message": f"No scheduled shift found for you at '{workplace.name}' within the current time window."
                    }
                )

        target_shift = candidate_shifts[0]

        # 4. Zero-Bypass FatigueGuard Validation
        FatigueGuardService.validate_qr_checkin(db, target_shift, checkin_time)

        # 5. Success: Transition shift to in_progress
        target_shift.status = "in_progress"
        target_shift.actual_start = checkin_time

        # Record CheckinEvent
        checkin_event = CheckinEvent(
            shift_id=target_shift.id,
            worker_id=worker_id,
            workplace_id=workplace.id,
            event_type="check_in",
            timestamp=checkin_time,
            verification_status="verified",
            scanned_site_token=scanned_site_token[:32] + "...",
            recorded_latitude=latitude,
            recorded_longitude=longitude,
            details=f"Successful QR check-in at {workplace.name}"
        )
        db.add(checkin_event)
        db.commit()
        db.refresh(target_shift)

        return {
            "success": True,
            "status": "in_progress",
            "shift_id": target_shift.id,
            "workplace_name": workplace.name,
            "actual_start": checkin_time.isoformat(),
            "physical_access_note": "Verification and attendance recorded. FairShift audits worker safety and shift compliance; physical site access is governed by local site protocols."
        }

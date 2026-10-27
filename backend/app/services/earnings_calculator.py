from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, Dict, Any

from app.models.shift import Shift
from app.models.earnings import EarningsLedger, Deduction

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class EarningsCalculator:
    STANDARD_REGULAR_HOURS_PER_DAY = Decimal("8.00")

    @staticmethod
    def round_currency(val: Decimal) -> Decimal:
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_shift_earnings(
        db: Session,
        shift: Shift,
        actual_start: datetime,
        actual_end: datetime
    ) -> EarningsLedger:
        """Computes regular hours, overtime hours, gross pay, deductions, and net pay for a completed shift."""
        actual_start = ensure_utc(actual_start)
        actual_end = ensure_utc(actual_end)
        if actual_end <= actual_start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Check-out time must be after check-in time."
            )

        duration_seconds = (actual_end - actual_start).total_seconds()
        duration_hours = Decimal(str(round(duration_seconds / 3600.0, 2)))

        # Split into regular vs overtime
        if duration_hours > EarningsCalculator.STANDARD_REGULAR_HOURS_PER_DAY:
            regular_hours = EarningsCalculator.STANDARD_REGULAR_HOURS_PER_DAY
            overtime_hours = duration_hours - EarningsCalculator.STANDARD_REGULAR_HOURS_PER_DAY
        else:
            regular_hours = duration_hours
            overtime_hours = Decimal("0.00")

        base_rate = Decimal(str(shift.base_hourly_rate))
        ot_multiplier = Decimal(str(shift.overtime_rate_multiplier))

        regular_pay = regular_hours * base_rate
        overtime_pay = overtime_hours * base_rate * ot_multiplier
        gross_pay = EarningsCalculator.round_currency(regular_pay + overtime_pay)

        # Check existing ledger entry if already created
        ledger = db.query(EarningsLedger).filter(EarningsLedger.shift_id == shift.id).first()
        if not ledger:
            ledger = EarningsLedger(
                shift_id=shift.id,
                worker_id=shift.worker_id,
                regular_hours=regular_hours,
                overtime_hours=overtime_hours,
                gross_pay=gross_pay,
                total_deductions=Decimal("0.00"),
                net_pay=gross_pay,  # Initial invariant: net_pay = gross_pay - 0
                currency="USD",
                payment_status="pending"
            )
            db.add(ledger)
        else:
            ledger.regular_hours = regular_hours
            ledger.overtime_hours = overtime_hours
            ledger.gross_pay = gross_pay
            # Recalculate net_pay invariant with existing deductions
            ledger.net_pay = EarningsCalculator.round_currency(gross_pay - Decimal(str(ledger.total_deductions)))

        db.commit()
        db.refresh(ledger)
        return ledger

    @staticmethod
    def add_deduction(
        db: Session,
        ledger: EarningsLedger,
        category: str,
        amount: Decimal,
        description: str,
        authorization_doc_ref: Optional[str] = None
    ) -> Deduction:
        """Enforces:
        1. amount > 0
        2. total_deductions + amount <= gross_pay
        3. net_pay = gross_pay - total_deductions
        """
        amount = EarningsCalculator.round_currency(amount)
        if amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Deduction amount must be strictly greater than $0.00."
            )

        current_total = Decimal(str(ledger.total_deductions))
        gross = Decimal(str(ledger.gross_pay))
        new_total = current_total + amount

        if new_total > gross:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid deduction: Total deductions (${new_total}) cannot exceed gross pay (${gross})."
            )

        deduction = Deduction(
            ledger_id=ledger.id,
            category=category,
            amount=amount,
            description=description,
            authorization_doc_ref=authorization_doc_ref
        )
        db.add(deduction)

        # Update ledger totals & enforce arithmetic invariant
        ledger.total_deductions = new_total
        ledger.net_pay = EarningsCalculator.round_currency(gross - new_total)

        db.commit()
        db.refresh(ledger)
        db.refresh(deduction)
        return deduction

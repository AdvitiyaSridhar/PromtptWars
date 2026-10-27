import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, init_db
from app.models.user import User
from app.models.organization import Organization
from app.models.fatigue_policy import FatiguePolicy
from app.models.workplace import Workplace
from app.models.shift import Shift, CheckinEvent, FatigueExceptionLog, AttendanceAttempt
from app.models.earnings import EarningsLedger, Deduction
from app.models.safety import SafetyReport, SafetyAction
from app.models.dispute import PayDispute
from app.models.evidence import EvidenceFile
from app.auth.security import hash_password

def seed(reset=False):
    init_db()
    db = SessionLocal()

    if not reset and db.query(User).count():
        demo_account = db.query(User).filter(
            User.email.in_([
                "admin.sarah@fairshift.demo",
                "admin.priya@fairshift.demo",
                "worker.carlos@fairshift.demo",
                "worker.amina@fairshift.demo",
            ])
        ).first()
        if demo_account:
            print("FairShift demo accounts already exist; leaving data unchanged.")
        else:
            print("Database contains user data. Refusing to overwrite it; pass --reset only if deletion is intended.")
        db.close()
        return
    if not reset and (db.query(Workplace).count() or db.query(FatiguePolicy).count()):
        print("Database contains operational data. Refusing to modify it; pass --reset only if deletion is intended.")
        db.close()
        return
    if not reset:
        db.query(Organization).filter(Organization.name.like("Legacy %")).delete(synchronize_session=False)
        db.commit()

    print("Cleaning and reseeding FairShift database...")
    if reset:
        db.query(PayDispute).delete()
        db.query(Deduction).delete()
        db.query(EarningsLedger).delete()
        db.query(CheckinEvent).delete()
        db.query(AttendanceAttempt).delete()
        db.query(FatigueExceptionLog).delete()
        db.query(SafetyAction).delete()
        db.query(SafetyReport).delete()
        db.query(EvidenceFile).delete()
        db.query(Shift).delete()
        db.query(Workplace).delete()
        db.query(FatiguePolicy).delete()
        db.query(User).delete()
        db.query(Organization).delete()
        db.commit()

    construction_org = Organization(name="Metro Construction Services", industry_sector="construction")
    gig_org = Organization(name="Northstar Delivery Platform", industry_sector="gig_platform")
    db.add_all([construction_org, gig_org])
    db.commit()

    # 1. Create organization-specific fatigue policies
    policy_construction = FatiguePolicy(
        organization_id=construction_org.id,
        policy_name="Construction Demo Policy",
        industry_sector="construction",
        max_daily_hours=10.0,
        min_rest_hours_between_shifts=11.0,
        max_weekly_hours=50.0,
        mandatory_break_threshold_hours=4.5,
        mandatory_break_duration_minutes=30.0,
        max_consecutive_days=6
    )
    policy_gig = FatiguePolicy(
        organization_id=gig_org.id,
        policy_name="Gig Platform Demo Policy",
        industry_sector="gig_platform",
        max_daily_hours=12.0,
        min_rest_hours_between_shifts=8.0,
        max_weekly_hours=60.0,
        mandatory_break_threshold_hours=4.0,
        mandatory_break_duration_minutes=30.0,
        max_consecutive_days=6
    )
    db.add_all([policy_construction, policy_gig])
    db.commit()

    # 2. Create Workplaces
    site_metro = Workplace(
        organization_id=construction_org.id,
        name="Metro Tower Phase 2 Construction",
        industry_sector="construction",
        address="450 Broadway St, Downtown Metro",
        latitude=40.7128,
        longitude=-74.0060,
        fatigue_policy_id=policy_construction.id,
        site_qr_secret="metro_tower_secure_qr_2026"
    )
    site_dispatch = Workplace(
        organization_id=gig_org.id,
        name="North Hub Urban Dispatch Center",
        industry_sector="gig_platform",
        address="1200 Industrial Parkway, Dock 4",
        latitude=40.7589,
        longitude=-73.9851,
        fatigue_policy_id=policy_gig.id,
        site_qr_secret="north_hub_secure_qr_2026"
    )
    db.add_all([site_metro, site_dispatch])
    db.commit()

    # 3. Create Users
    admin_sarah = User(
        organization_id=construction_org.id,
        email="admin.sarah@fairshift.demo",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Sarah Jenkins",
        role="employer_admin",
        industry_sector="construction",
        phone_number="555-0101"
    )
    safety_marcus = User(
        organization_id=construction_org.id,
        email="safety.marcus@fairshift.demo",
        hashed_password=hash_password("SafetyPass123!"),
        full_name="Marcus Vance",
        role="safety_officer",
        industry_sector="construction",
        phone_number="555-0102"
    )
    worker_carlos = User(
        organization_id=construction_org.id,
        email="worker.carlos@fairshift.demo",
        hashed_password=hash_password("WorkerPass123!"),
        full_name="Carlos Mendez",
        role="worker",
        industry_sector="construction",
        phone_number="555-0103"
    )
    worker_amina = User(
        organization_id=gig_org.id,
        email="worker.amina@fairshift.demo",
        hashed_password=hash_password("WorkerPass123!"),
        full_name="Amina Patel",
        role="worker",
        industry_sector="gig_platform",
        phone_number="555-0104"
    )
    admin_priya = User(
        organization_id=gig_org.id,
        email="admin.priya@fairshift.demo",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Priya Shah",
        role="employer_admin",
        industry_sector="gig_platform",
        phone_number="555-0105"
    )
    db.add_all([admin_sarah, safety_marcus, worker_carlos, worker_amina, admin_priya])
    db.commit()

    now = datetime.now(timezone.utc)

    # 4. Shifts for Carlos Mendez (Construction)
    # Yesterday's completed shift: 08:00 to 17:30 (9.5 hours: 8.0 reg + 1.5 OT)
    yesterday_start = (now - timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    yesterday_end = (now - timedelta(days=1)).replace(hour=17, minute=30, second=0, microsecond=0)

    shift_carlos_past = Shift(
        worker_id=worker_carlos.id,
        workplace_id=site_metro.id,
        created_by=admin_sarah.id,
        scheduled_start=yesterday_start,
        scheduled_end=yesterday_end,
        actual_start=yesterday_start,
        actual_end=yesterday_end,
        base_hourly_rate=Decimal("26.00"),
        overtime_rate_multiplier=Decimal("1.50"),
        status="completed"
    )
    db.add(shift_carlos_past)
    db.commit()

    # Yesterday's Ledger & Deduction for Carlos
    reg_pay = Decimal("8.00") * Decimal("26.00")  # 208.00
    ot_pay = Decimal("1.50") * Decimal("26.00") * Decimal("1.50")  # 58.50
    gross = reg_pay + ot_pay  # 266.50
    deduction_amt = Decimal("35.00")
    net = gross - deduction_amt  # 231.50

    ledger_carlos = EarningsLedger(
        shift_id=shift_carlos_past.id,
        worker_id=worker_carlos.id,
        regular_hours=Decimal("8.00"),
        overtime_hours=Decimal("1.50"),
        gross_pay=gross,
        total_deductions=deduction_amt,
        net_pay=net,
        currency="USD",
        payment_status="approved",
        payment_reference="PAY-2026-METRO-0042"
    )
    db.add(ledger_carlos)
    db.commit()

    deduction_carlos = Deduction(
        ledger_id=ledger_carlos.id,
        category="equipment_rental",
        amount=deduction_amt,
        description="Daily heavy fall-arrest harness rental fee",
        authorization_doc_ref="TOOL-CRIB-RECEIPT-9081"
    )
    db.add(deduction_carlos)

    # Carlos's Active Pay Dispute on the deduction
    dispute_carlos = PayDispute(
        worker_id=worker_carlos.id,
        shift_id=shift_carlos_past.id,
        ledger_id=ledger_carlos.id,
        dispute_type="unauthorized_deduction",
        claimed_amount=Decimal("35.00"),
        worker_explanation="Under Article 4 of site subcontract agreement, fall-arrest harnesses are employer-provided PPE and exempt from daily rental charges.",
        status="under_review"
    )
    db.add(dispute_carlos)

    # Today's Shift for Carlos: Scheduled around current hour so he can test QR Check-In immediately!
    today_start = now.replace(minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(hours=8)
    shift_carlos_today = Shift(
        worker_id=worker_carlos.id,
        workplace_id=site_metro.id,
        created_by=admin_sarah.id,
        scheduled_start=today_start,
        scheduled_end=today_end,
        base_hourly_rate=Decimal("26.00"),
        overtime_rate_multiplier=Decimal("1.50"),
        status="scheduled"
    )
    db.add(shift_carlos_today)

    # 5. Shifts for Amina Patel (Gig Platform Courier)
    # Amina has an in-progress shift at North Hub
    shift_amina_active = Shift(
        worker_id=worker_amina.id,
        workplace_id=site_dispatch.id,
        created_by=admin_priya.id,
        scheduled_start=now - timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
        actual_start=now - timedelta(hours=3),
        base_hourly_rate=Decimal("22.50"),
        overtime_rate_multiplier=Decimal("1.50"),
        status="in_progress"
    )
    db.add(shift_amina_active)

    # 6. Safety Report & Corrective Action
    safety_report = SafetyReport(
        reporter_id=worker_carlos.id,
        workplace_id=site_metro.id,
        shift_id=shift_carlos_past.id,
        category="hazard",
        severity="high",
        title="Scaffolding missing toe-boards on Level 4 near pedestrian access",
        description="Scaffolding planking has a 6-inch gap without toe-boards above the ground-level walkway. Dropped tools pose severe strike hazard to ground crews.",
        is_anonymous=False,
        status="corrective_action_pending",
        assigned_to=safety_marcus.id
    )
    db.add(safety_report)
    db.commit()

    action_remedy = SafetyAction(
        report_id=safety_report.id,
        action_description="Install 4-inch wood toe-boards and safety debris netting along Level 4 perimeter scaffold.",
        assigned_to=safety_marcus.id,
        due_date=(now + timedelta(days=1)).date()
    )
    db.add(action_remedy)

    # 7. Auditable Fatigue Exception Log
    # Simulates an earlier attempt by an admin to assign Carlos an early morning shift that was rejected
    fatigue_log = FatigueExceptionLog(
        worker_id=worker_carlos.id,
        shift_id=None,
        workplace_id=site_metro.id,
        attempted_action="shift_assignment",
        timestamp=now - timedelta(days=2),
        breach_type="insufficient_rest",
        hours_worked_past_24h=9.5,
        rest_hours_elapsed=6.0,
        policy_required_rest=11.0,
        policy_max_daily=10.0,
        rejection_reason="REJECTED BY FATIGUEGUARD: Attempted shift allowed only 6.0h rest after a 9.5h shift. Policy 'Construction Standard' strictly requires 11.0h rest.",
        reviewed_by_admin=True,
        admin_audit_notes="Confirmed rejection. Reassigned shift to secondary contractor to preserve mandatory rest hours."
    )
    db.add(fatigue_log)
    db.commit()
    db.close()

    print("FairShift demo data seeded successfully!")
    print("-----------------------------------------------------------------")
    print("DEMO CREDENTIALS:")
    print("  Worker (Construction): worker.carlos@fairshift.demo   / WorkerPass123!")
    print("  Worker (Gig Courier):   worker.amina@fairshift.demo    / WorkerPass123!")
    print("  Admin / Supervisor:     admin.sarah@fairshift.demo     / AdminPass123!")
    print("  Gig Platform Admin:     admin.priya@fairshift.demo     / AdminPass123!")
    print("  Safety Officer:         safety.marcus@fairshift.demo   / SafetyPass123!")
    print("-----------------------------------------------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed FairShift demonstration organizations.")
    parser.add_argument("--reset", action="store_true", help="Delete existing records before reseeding.")
    seed(reset=parser.parse_args().reset)

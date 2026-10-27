import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.services.qr_service import QRService
from app.models.shift import Shift, FatigueExceptionLog
from app.models.shift import CheckinEvent, AttendanceAttempt
from app.models.earnings import EarningsLedger, Deduction

def test_login_worker_and_admin(client, test_setup_data):
    """1. Verify successful login for worker and admin accounts."""
    # Worker login
    resp = client.post("/api/v1/auth/login", json={
        "email": "test.worker1@fairshift.test",
        "password": "Password123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "worker"

    # Admin login
    resp_admin = client.post("/api/v1/auth/login", json={
        "email": "test.admin@fairshift.test",
        "password": "Password123!"
    })
    assert resp_admin.status_code == 200
    assert resp_admin.json()["user"]["role"] == "employer_admin"


def test_workers_cannot_access_admin_endpoints(client, test_setup_data):
    """2. Verify workers cannot access admin-only endpoints."""
    worker_headers = test_setup_data["worker1_headers"]

    # Worker attempting to create a shift
    resp = client.post("/api/v1/shifts", headers=worker_headers, json={
        "worker_id": test_setup_data["worker1"].id,
        "workplace_id": test_setup_data["site_alpha"].id,
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "scheduled_end": (datetime.now(timezone.utc) + timedelta(days=1, hours=8)).isoformat()
    })
    assert resp.status_code == 403

    # Worker attempting to view admin payroll ledger
    resp_ledger = client.get("/api/v1/ledger/admin", headers=worker_headers)
    assert resp_ledger.status_code == 403

    # Worker attempting to view fatigue exception audit logs
    resp_exceptions = client.get("/api/v1/fatigue/exceptions", headers=worker_headers)
    assert resp_exceptions.status_code == 403


def test_workers_cannot_access_other_worker_records(client, test_setup_data):
    """3. Verify workers cannot view or tamper with another worker's private records."""
    worker1_headers = test_setup_data["worker1_headers"]
    worker2 = test_setup_data["worker2"]

    # Worker 1 attempting to view Worker 2's fatigue eligibility
    resp = client.get(f"/api/v1/fatigue/eligibility/{worker2.id}", headers=worker1_headers)
    assert resp.status_code == 403

def test_organizations_are_isolated(client, test_setup_data):
    """Admins and workers cannot use IDs from another organization."""
    data = test_setup_data
    admin_headers = data["admin_headers"]
    worker_headers = data["worker1_headers"]

    sites = client.get("/api/v1/workplaces", headers=admin_headers)
    assert sites.status_code == 200
    assert {site["id"] for site in sites.json()} == {data["site_alpha"].id}

    qr = client.get(
        f"/api/v1/workplaces/{data['site_beta'].id}/site-qr",
        headers=admin_headers
    )
    assert qr.status_code == 404

    assignment = client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": data["worker2"].id,
        "workplace_id": data["site_beta"].id,
        "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "scheduled_end": (datetime.now(timezone.utc) + timedelta(days=2, hours=8)).isoformat()
    })
    assert assignment.status_code == 404

    foreign_eligibility = client.get(
        f"/api/v1/fatigue/eligibility/{data['worker2'].id}",
        headers=worker_headers
    )
    assert foreign_eligibility.status_code == 403

    foreign_report = client.post("/api/v1/safety/reports", headers=worker_headers, json={
        "workplace_id": data["site_beta"].id,
        "category": "hazard",
        "title": "Foreign organization hazard",
        "description": "This report must not be associated with another company site."
    })
    assert foreign_report.status_code == 404

    cross_company_token = QRService.generate_site_qr_token(data["site_beta"])
    cross_company_scan = client.post("/api/v1/shifts/check-in", headers=worker_headers, json={
        "scanned_site_token": cross_company_token
    })
    assert cross_company_scan.status_code == 404

def test_public_registration_cannot_create_accounts_or_privileged_roles(client):
    response = client.post("/api/v1/auth/register", json={
        "email": "new.admin@untrusted.test",
        "password": "Password123!",
        "full_name": "Untrusted Admin",
        "role": "employer_admin",
        "industry_sector": "construction"
    })
    assert response.status_code == 403


def test_valid_shift_creation_and_assignment(client, test_setup_data):
    """4. Verify a valid shift can be created and assigned by an authorized admin."""
    admin_headers = test_setup_data["admin_headers"]
    worker = test_setup_data["worker1"]
    site = test_setup_data["site_alpha"]

    start = datetime.now(timezone.utc) + timedelta(days=2, hours=8)
    end = start + timedelta(hours=8)

    resp = client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": worker.id,
        "workplace_id": site.id,
        "scheduled_start": start.isoformat(),
        "scheduled_end": end.isoformat(),
        "base_hourly_rate": 25.00,
        "overtime_rate_multiplier": 1.50
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["worker_id"] == worker.id


def test_overlapping_shift_rejected(client, test_setup_data):
    """5. Verify overlapping or conflicting shifts are strictly rejected by the backend."""
    admin_headers = test_setup_data["admin_headers"]
    worker = test_setup_data["worker1"]
    site = test_setup_data["site_alpha"]

    start1 = datetime.now(timezone.utc) + timedelta(days=5, hours=8)
    end1 = start1 + timedelta(hours=8)

    # First shift
    resp1 = client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": worker.id,
        "workplace_id": site.id,
        "scheduled_start": start1.isoformat(),
        "scheduled_end": end1.isoformat()
    })
    assert resp1.status_code == 201

    # Overlapping shift (starts 2 hours into shift 1)
    overlap_start = start1 + timedelta(hours=2)
    overlap_end = overlap_start + timedelta(hours=6)
    resp2 = client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": worker.id,
        "workplace_id": site.id,
        "scheduled_start": overlap_start.isoformat(),
        "scheduled_end": overlap_end.isoformat()
    })
    assert resp2.status_code == 422
    err = resp2.json()["detail"]
    assert err["code"] == "FATIGUE_LIMIT_BREACHED"
    assert err["breach_type"] == "overlapping_shifts"


def test_unsafe_assignment_insufficient_rest_rejected(client, test_setup_data):
    """6. Verify unsafe assignment with insufficient rest is rejected even if called directly via API."""
    admin_headers = test_setup_data["admin_headers"]
    worker = test_setup_data["worker1"]
    site = test_setup_data["site_alpha"]  # Construction: requires 11h rest

    # Shift 1: 08:00 to 18:00 (10 hours)
    start1 = datetime.now(timezone.utc) + timedelta(days=10, hours=8)
    end1 = start1 + timedelta(hours=10)
    resp1 = client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": worker.id,
        "workplace_id": site.id,
        "scheduled_start": start1.isoformat(),
        "scheduled_end": end1.isoformat()
    })
    assert resp1.status_code == 201

    # Shift 2: Only 6 hours later (at 00:00 next day) -> Breaches 11h rest requirement!
    unsafe_start = end1 + timedelta(hours=6)
    unsafe_end = unsafe_start + timedelta(hours=8)
    resp2 = client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": worker.id,
        "workplace_id": site.id,
        "scheduled_start": unsafe_start.isoformat(),
        "scheduled_end": unsafe_end.isoformat()
    })
    assert resp2.status_code == 422
    err = resp2.json()["detail"]
    assert err["code"] == "FATIGUE_LIMIT_BREACHED"
    assert err["breach_type"] == "insufficient_rest"
    assert "Insufficient rest" in err["reason"]


def test_qr_checkin_and_checkout_flow(client, test_setup_data, db_session):
    """7, 8, 9, 10. Test full QR attendance flow, invalid token, out-of-window, and duplicate scan."""
    admin_headers = test_setup_data["admin_headers"]
    worker = test_setup_data["worker1"]
    worker_headers = test_setup_data["worker1_headers"]
    site = test_setup_data["site_alpha"]

    # 1. Invalid / tampered QR token rejected
    bad_token_resp = client.post("/api/v1/shifts/check-in", headers=worker_headers, json={
        "scanned_site_token": "tampered_invalid_token_xyz"
    })
    assert bad_token_resp.status_code == 400
    assert db_session.query(AttendanceAttempt).filter_by(outcome_code="rejected_invalid_qr").count() == 1

    # 2. Out of window check-in rejected (shift scheduled 3 days in advance)
    future_start = datetime.now(timezone.utc) + timedelta(days=15)
    future_end = future_start + timedelta(hours=8)
    client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": worker.id,
        "workplace_id": site.id,
        "scheduled_start": future_start.isoformat(),
        "scheduled_end": future_end.isoformat()
    })

    site_qr_token = QRService.generate_site_qr_token(site)
    out_of_window_resp = client.post("/api/v1/shifts/check-in", headers=worker_headers, json={
        "scanned_site_token": site_qr_token
    })
    assert out_of_window_resp.status_code == 422
    assert out_of_window_resp.json()["detail"]["code"] == "SCHEDULE_WINDOW_INVALID"
    assert db_session.query(AttendanceAttempt).filter_by(outcome_code="rejected_window").count() == 1

    # 3. Create a shift scheduled right now
    now = datetime.now(timezone.utc)
    current_shift_resp = client.post("/api/v1/shifts", headers=admin_headers, json={
        "worker_id": worker.id,
        "workplace_id": site.id,
        "scheduled_start": (now - timedelta(minutes=10)).isoformat(),
        "scheduled_end": (now + timedelta(hours=8)).isoformat(),
        "base_hourly_rate": 30.00,
        "overtime_rate_multiplier": 1.50
    })
    assert current_shift_resp.status_code == 201
    shift_id = current_shift_resp.json()["id"]

    # 4. Valid QR Check-In succeeds
    valid_checkin_resp = client.post("/api/v1/shifts/check-in", headers=worker_headers, json={
        "scanned_site_token": site_qr_token
    })
    assert valid_checkin_resp.status_code == 200
    checkin_data = valid_checkin_resp.json()
    assert checkin_data["success"] is True
    assert checkin_data["status"] == "in_progress"
    assert "Verification and attendance recorded" in checkin_data["physical_access_note"]
    assert db_session.query(CheckinEvent).filter_by(
        shift_id=shift_id,
        event_type="check_in",
        verification_status="verified"
    ).count() == 1

    # 5. Duplicate Check-In rejected (Worker already checked in)
    duplicate_resp = client.post("/api/v1/shifts/check-in", headers=worker_headers, json={
        "scanned_site_token": site_qr_token
    })
    assert duplicate_resp.status_code == 409
    assert duplicate_resp.json()["detail"]["code"] == "ALREADY_CHECKED_IN"

    # 6. Check-Out computes duration and initializes Earnings Ledger
    wrong_site_checkout = client.post(
        f"/api/v1/shifts/{shift_id}/check-out",
        headers=worker_headers,
        json={"scanned_site_token": QRService.generate_site_qr_token(test_setup_data["site_beta"])}
    )
    assert wrong_site_checkout.status_code == 403
    checkout_resp = client.post(
        f"/api/v1/shifts/{shift_id}/check-out",
        headers=worker_headers,
        json={"scanned_site_token": site_qr_token}
    )
    assert checkout_resp.status_code == 200
    checkout_data = checkout_resp.json()
    assert checkout_data["status"] == "completed"
    assert checkout_data["duration_hours"] >= 0.0


def test_ledger_net_pay_arithmetic_invariant_and_deductions(client, test_setup_data, db_session):
    """11, 12. Verify ledger net-pay invariant: net_pay = gross_pay - total_deductions and deduction rules."""
    admin_headers = test_setup_data["admin_headers"]
    worker = test_setup_data["worker1"]
    worker_headers = test_setup_data["worker1_headers"]
    site = test_setup_data["site_alpha"]

    # Create & complete a shift
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=9)
    end = now
    shift = Shift(
        worker_id=worker.id,
        workplace_id=site.id,
        created_by=test_setup_data["admin"].id,
        scheduled_start=start,
        scheduled_end=end,
        actual_start=start,
        actual_end=end,
        base_hourly_rate=Decimal("20.00"),
        overtime_rate_multiplier=Decimal("1.50"),
        status="in_progress"
    )
    db_session.add(shift)
    db_session.commit()

    # Worker checks out
    checkout_resp = client.post(f"/api/v1/shifts/{shift.id}/check-out", headers=worker_headers)
    assert checkout_resp.status_code == 200

    # Retrieve ledger
    ledger_resp = client.get("/api/v1/ledger/worker", headers=worker_headers)
    assert ledger_resp.status_code == 200
    ledger_entries = ledger_resp.json()
    assert len(ledger_entries) > 0
    ledger = ledger_entries[0]
    ledger_id = ledger["id"]

    # Arithmetic check: 9 hours = 8.0 regular ($160) + 1.0 overtime ($30) = $190 gross
    assert Decimal(str(ledger["gross_pay"])) == Decimal("190.00")
    assert Decimal(str(ledger["net_pay"])) == Decimal("190.00")

    # Worker attempting to add deduction to their own ledger -> FORBIDDEN (403)
    worker_deduct_resp = client.post(f"/api/v1/ledger/{ledger_id}/deductions", headers=worker_headers, json={
        "category": "uniform",
        "amount": 25.00,
        "description": "Unauthorized worker self-deduction"
    })
    assert worker_deduct_resp.status_code == 403

    # Admin adds negative deduction -> REJECTED (422)
    neg_deduct = client.post(f"/api/v1/ledger/{ledger_id}/deductions", headers=admin_headers, json={
        "category": "uniform",
        "amount": -25.00,
        "description": "Negative deduction"
    })
    assert neg_deduct.status_code == 422

    # Admin adds deduction exceeding gross ($200 > $190) -> REJECTED (422)
    excess_deduct = client.post(f"/api/v1/ledger/{ledger_id}/deductions", headers=admin_headers, json={
        "category": "equipment_rental",
        "amount": 200.00,
        "description": "Excess deduction"
    })
    assert excess_deduct.status_code == 422

    # Admin adds legitimate deduction of $40.00
    valid_deduct = client.post(f"/api/v1/ledger/{ledger_id}/deductions", headers=admin_headers, json={
        "category": "equipment_rental",
        "amount": 40.00,
        "description": "Safety boots rental",
        "authorization_doc_ref": "RECEIPT-881"
    })
    assert valid_deduct.status_code == 201

    # Verify arithmetic invariant: net_pay = gross - deductions (190 - 40 = 150)
    worker_ledger_updated = client.get("/api/v1/ledger/worker", headers=worker_headers).json()[0]
    assert Decimal(str(worker_ledger_updated["gross_pay"])) == Decimal("190.00")
    assert Decimal(str(worker_ledger_updated["total_deductions"])) == Decimal("40.00")
    assert Decimal(str(worker_ledger_updated["net_pay"])) == Decimal("150.00")
    assert (Decimal(str(worker_ledger_updated["gross_pay"])) - Decimal(str(worker_ledger_updated["total_deductions"]))) == Decimal(str(worker_ledger_updated["net_pay"]))

    paid_too_early = client.patch(f"/api/v1/ledger/{ledger_id}/status", headers=admin_headers, json={
        "payment_status": "paid",
        "payment_reference": "PAY-TEST"
    })
    assert paid_too_early.status_code == 409
    approved = client.patch(f"/api/v1/ledger/{ledger_id}/status", headers=admin_headers, json={
        "payment_status": "approved"
    })
    assert approved.status_code == 200
    missing_reference = client.patch(f"/api/v1/ledger/{ledger_id}/status", headers=admin_headers, json={
        "payment_status": "paid"
    })
    assert missing_reference.status_code == 422
    paid = client.patch(f"/api/v1/ledger/{ledger_id}/status", headers=admin_headers, json={
        "payment_status": "paid",
        "payment_reference": "PAY-TEST-001"
    })
    assert paid.status_code == 200
    assert paid.json()["payment_status"] == "paid"


def test_safety_and_disputes_workflow(client, test_setup_data, db_session):
    """13, 14. Verify safety reporting, corrective actions, dispute filing and automated settlement."""
    worker = test_setup_data["worker1"]
    worker_headers = test_setup_data["worker1_headers"]
    admin_headers = test_setup_data["admin_headers"]
    site = test_setup_data["site_alpha"]

    # 1. Worker submits safety hazard report
    report_resp = client.post("/api/v1/safety/reports", headers=worker_headers, json={
        "workplace_id": site.id,
        "category": "hazard",
        "severity": "critical",
        "title": "Exposed high voltage conduit near wet floor",
        "description": "Temporary power line has frayed insulation touching puddle in basement.",
        "is_anonymous": True
    })
    assert report_resp.status_code == 201
    report = report_resp.json()
    report_id = report["id"]
    assert report["is_anonymous"] is True

    # 2. Admin adds corrective action
    action_resp = client.post(f"/api/v1/safety/reports/{report_id}/actions", headers=admin_headers, json={
        "action_description": "Lockout electrical circuit and reroute waterproof cabling.",
        "assigned_to": test_setup_data["admin"].id,
        "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
    })
    assert action_resp.status_code == 201
    action_id = action_resp.json()["id"]

    # 3. Admin resolves corrective action
    resolve_resp = client.patch(f"/api/v1/safety/actions/{action_id}/resolve", headers=admin_headers, json={
        "verification_notes": "Circuit de-energized, cable elevated and sealed. Passed safety inspection."
    })
    assert resolve_resp.status_code == 200

    # 4. Dispute filing & settlement: Worker files dispute on a completed shift
    now = datetime.now(timezone.utc)
    shift = Shift(
        worker_id=worker.id,
        workplace_id=site.id,
        created_by=test_setup_data["admin"].id,
        scheduled_start=now - timedelta(hours=6),
        scheduled_end=now,
        actual_start=now - timedelta(hours=6),
        actual_end=now,
        base_hourly_rate=Decimal("20.00"),
        overtime_rate_multiplier=Decimal("1.50"),
        status="completed"
    )
    db_session.add(shift)
    db_session.commit()

    ledger = EarningsLedger(
        shift_id=shift.id,
        worker_id=worker.id,
        regular_hours=Decimal("6.00"),
        overtime_hours=Decimal("0.00"),
        gross_pay=Decimal("120.00"),
        total_deductions=Decimal("0.00"),
        net_pay=Decimal("120.00")
    )
    db_session.add(ledger)
    db_session.commit()

    dispute_resp = client.post("/api/v1/disputes", headers=worker_headers, json={
        "shift_id": shift.id,
        "ledger_id": ledger.id,
        "dispute_type": "unpaid_hours",
        "claimed_amount": 40.00,
        "worker_explanation": "Shift included 2 hours of mandatory pre-shift safety staging not counted on timecard."
    })
    assert dispute_resp.status_code == 201
    dispute_id = dispute_resp.json()["id"]

    # 5. Admin upholds dispute with settlement amount
    settle_resp = client.patch(f"/api/v1/disputes/{dispute_id}/review", headers=admin_headers, json={
        "status": "resolved_upheld",
        "settled_amount": 40.00,
        "resolution_notes": "Supervisor verified 2 hours unpaid safety staging. Upheld in full."
    })
    assert settle_resp.status_code == 200
    settled = settle_resp.json()
    assert settled["status"] == "resolved_upheld"
    assert Decimal(str(settled["settled_amount"])) == Decimal("40.00")

    # 6. Verify automated ledger settlement adjustment
    db_session.refresh(ledger)
    assert Decimal(str(ledger.net_pay)) == Decimal("160.00")  # 120 + 40
    assert "Dispute" in ledger.payment_reference


def test_ineligible_worker_blocked_at_qr_checkin(client, test_setup_data, db_session):
    """Verify zero-bypass FatigueGuard: A worker attempting to check in via QR with insufficient rest is rejected with 422 and audited."""
    worker = test_setup_data["worker1"]
    worker_headers = test_setup_data["worker1_headers"]
    site = test_setup_data["site_alpha"]  # Construction requires 11h rest

    now = datetime.now(timezone.utc)
    # Simulate a shift that ended only 4 hours ago
    prior_shift = Shift(
        worker_id=worker.id,
        workplace_id=site.id,
        created_by=test_setup_data["admin"].id,
        scheduled_start=now - timedelta(hours=12),
        scheduled_end=now - timedelta(hours=4),
        actual_start=now - timedelta(hours=12),
        actual_end=now - timedelta(hours=4),
        status="completed"
    )
    db_session.add(prior_shift)

    # Shift starting right now
    current_shift = Shift(
        worker_id=worker.id,
        workplace_id=site.id,
        created_by=test_setup_data["admin"].id,
        scheduled_start=now,
        scheduled_end=now + timedelta(hours=8),
        status="scheduled"
    )
    db_session.add(current_shift)
    db_session.commit()

    site_qr_token = QRService.generate_site_qr_token(site)
    resp = client.post("/api/v1/shifts/check-in", headers=worker_headers, json={
        "scanned_site_token": site_qr_token
    })

    # Must be strictly rejected with 422
    assert resp.status_code == 422
    data = resp.json()["detail"]
    assert data["code"] == "ELIGIBILITY_BLOCKED_FATIGUE"
    assert data["breach_type"] == "insufficient_rest"
    assert "Check-in blocked by FatigueGuard" in data["reason"]

    # Verify audit log entry was created
    log = db_session.query(FatigueExceptionLog).filter(
        FatigueExceptionLog.worker_id == worker.id,
        FatigueExceptionLog.attempted_action == "qr_check_in"
    ).first()
    assert log is not None
    assert log.breach_type == "insufficient_rest"
    assert log.policy_required_rest == 11.0


def test_data_persistence_across_app_context(test_setup_data):
    """Verify data persists in the database across separate sessions/connections."""
    from app.database import SessionLocal
    from app.models.user import User

    db1 = SessionLocal()
    new_user = User(
        email="persistent.test@fairshift.test",
        hashed_password="hashed_pass_test",
        full_name="Persistent User",
        role="worker",
        industry_sector="construction"
    )
    db1.add(new_user)
    db1.commit()
    user_id = new_user.id
    db1.close()

    # Open fresh second session
    db2 = SessionLocal()
    fetched = db2.query(User).filter(User.id == user_id).first()
    assert fetched is not None
    assert fetched.full_name == "Persistent User"

    # Clean up
    db2.delete(fetched)
    db2.commit()
    db2.close()

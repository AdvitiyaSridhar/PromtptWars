import pytest
import os
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.fatigue_policy import FatiguePolicy
from app.models.workplace import Workplace
from app.models.shift import Shift, CheckinEvent, FatigueExceptionLog, AttendanceAttempt
from app.models.earnings import EarningsLedger, Deduction
from app.models.safety import SafetyReport, SafetyAction
from app.models.dispute import PayDispute
from app.auth.security import hash_password, create_access_token

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture(autouse=True)
def clean_test_state():
    session = TestingSessionLocal()
    session.query(PayDispute).delete()
    session.query(Deduction).delete()
    session.query(EarningsLedger).delete()
    session.query(CheckinEvent).delete()
    session.query(AttendanceAttempt).delete()
    session.query(FatigueExceptionLog).delete()
    session.query(SafetyAction).delete()
    session.query(SafetyReport).delete()
    session.query(Shift).delete()
    session.commit()
    session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_setup_data(db_session):
    construction_org = db_session.query(Organization).filter_by(name="Test Construction Org").first()
    if not construction_org:
        construction_org = Organization(name="Test Construction Org", industry_sector="construction")
        db_session.add(construction_org)
    gig_org = db_session.query(Organization).filter_by(name="Test Gig Org").first()
    if not gig_org:
        gig_org = Organization(name="Test Gig Org", industry_sector="gig_platform")
        db_session.add(gig_org)
    db_session.flush()

    # Ensure policies exist
    policy_construction = db_session.query(FatiguePolicy).filter_by(industry_sector="construction").first()
    if not policy_construction:
        policy_construction = FatiguePolicy(
            organization_id=construction_org.id,
            policy_name="Test Construction Policy",
            industry_sector="construction",
            max_daily_hours=10.0,
            min_rest_hours_between_shifts=11.0,
            max_weekly_hours=50.0,
            mandatory_break_threshold_hours=4.5,
            mandatory_break_duration_minutes=30.0,
            max_consecutive_days=6
        )
        db_session.add(policy_construction)

    policy_gig = db_session.query(FatiguePolicy).filter_by(industry_sector="gig_platform").first()
    if not policy_gig:
        policy_gig = FatiguePolicy(
            organization_id=gig_org.id,
            policy_name="Test Gig Policy",
            industry_sector="gig_platform",
            max_daily_hours=12.0,
            min_rest_hours_between_shifts=8.0,
            max_weekly_hours=60.0,
            mandatory_break_threshold_hours=4.0,
            mandatory_break_duration_minutes=30.0,
            max_consecutive_days=6
        )
        db_session.add(policy_gig)
    
    db_session.flush()

    # Ensure workplaces exist
    site_alpha = db_session.query(Workplace).filter_by(name="Alpha Test Site").first()
    if not site_alpha:
        site_alpha = Workplace(
            organization_id=construction_org.id,
            name="Alpha Test Site",
            industry_sector="construction",
            address="100 Test Blvd",
            fatigue_policy_id=policy_construction.id,
            site_qr_secret="alpha_test_secret_key"
        )
        db_session.add(site_alpha)

    site_beta = db_session.query(Workplace).filter_by(name="Beta Courier Hub").first()
    if not site_beta:
        site_beta = Workplace(
            organization_id=gig_org.id,
            name="Beta Courier Hub",
            industry_sector="gig_platform",
            address="200 Warehouse Way",
            fatigue_policy_id=policy_gig.id,
            site_qr_secret="beta_test_secret_key"
        )
        db_session.add(site_beta)

    db_session.flush()

    # Ensure users exist
    admin = db_session.query(User).filter_by(email="test.admin@fairshift.test").first()
    if not admin:
        admin = User(
            organization_id=construction_org.id,
            email="test.admin@fairshift.test",
            hashed_password=hash_password("Password123!"),
            full_name="Test Admin",
            role="employer_admin",
            industry_sector="construction"
        )
        db_session.add(admin)

    worker_1 = db_session.query(User).filter_by(email="test.worker1@fairshift.test").first()
    if not worker_1:
        worker_1 = User(
            organization_id=construction_org.id,
            email="test.worker1@fairshift.test",
            hashed_password=hash_password("Password123!"),
            full_name="Worker One",
            role="worker",
            industry_sector="construction"
        )
        db_session.add(worker_1)

    worker_2 = db_session.query(User).filter_by(email="test.worker2@fairshift.test").first()
    if not worker_2:
        worker_2 = User(
            organization_id=gig_org.id,
            email="test.worker2@fairshift.test",
            hashed_password=hash_password("Password123!"),
            full_name="Worker Two",
            role="worker",
            industry_sector="gig_platform"
        )
        db_session.add(worker_2)

    db_session.commit()

    admin_token = create_access_token({"sub": admin.id, "email": admin.email, "role": admin.role})
    worker1_token = create_access_token({"sub": worker_1.id, "email": worker_1.email, "role": worker_1.role})
    worker2_token = create_access_token({"sub": worker_2.id, "email": worker_2.email, "role": worker_2.role})

    return {
        "admin": admin,
        "worker1": worker_1,
        "worker2": worker_2,
        "site_alpha": site_alpha,
        "site_beta": site_beta,
        "policy_construction": policy_construction,
        "policy_gig": policy_gig,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "worker1_headers": {"Authorization": f"Bearer {worker1_token}"},
        "worker2_headers": {"Authorization": f"Bearer {worker2_token}"}
    }

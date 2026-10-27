from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings
from typing import Generator

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_args = {}
if is_sqlite:
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    engine_args["pool_pre_ping"] = True
    engine_args["pool_size"] = 5
    engine_args["max_overflow"] = 10

database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(database_url, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    for table in ("users", "workplaces", "fatigue_policies"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "organization_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN organization_id VARCHAR(36)"))
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.workplace import Workplace
    from app.models.fatigue_policy import FatiguePolicy
    from app.models.shift import AttendanceAttempt

    attempt_columns = {column["name"] for column in inspect(engine).get_columns("attendance_attempts")}
    if "organization_id" not in attempt_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE attendance_attempts ADD COLUMN organization_id VARCHAR(36)"))

    with SessionLocal() as db:
        for sector in ("construction", "gig_platform"):
            has_unassigned_records = any(
                query.count()
                for query in (
                    db.query(User.id).filter(User.industry_sector == sector, User.organization_id.is_(None)),
                    db.query(Workplace.id).filter(Workplace.industry_sector == sector, Workplace.organization_id.is_(None)),
                    db.query(FatiguePolicy.id).filter(FatiguePolicy.industry_sector == sector, FatiguePolicy.organization_id.is_(None)),
                )
            )
            if not has_unassigned_records:
                continue
            organization = db.query(Organization).filter(
                Organization.name == f"Legacy {sector.replace('_', ' ').title()}"
            ).first()
            if not organization:
                organization = Organization(
                    name=f"Legacy {sector.replace('_', ' ').title()}",
                    industry_sector=sector
                )
                db.add(organization)
                db.flush()
            db.query(User).filter(
                User.industry_sector == sector,
                User.organization_id.is_(None)
            ).update({User.organization_id: organization.id}, synchronize_session=False)
            db.query(Workplace).filter(
                Workplace.industry_sector == sector,
                Workplace.organization_id.is_(None)
            ).update({Workplace.organization_id: organization.id}, synchronize_session=False)
            db.query(FatiguePolicy).filter(
                FatiguePolicy.industry_sector == sector,
                FatiguePolicy.organization_id.is_(None)
            ).update({FatiguePolicy.organization_id: organization.id}, synchronize_session=False)
        for attempt in db.query(AttendanceAttempt).filter(AttendanceAttempt.organization_id.is_(None)).all():
            if attempt.workplace and attempt.workplace.organization_id:
                attempt.organization_id = attempt.workplace.organization_id
        db.commit()

# ============================================================
# backend/database.py — SQLAlchemy Models + Async Session
# ============================================================
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarativeBase, relationship
import enum

from .config import settings

# ---- Engine & Session --------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarativeBase()


# ---- Enums -------------------------------------------------------------
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class CreditTransactionType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class CreditRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---- Models ------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    job_title = Column(String(150))
    internal_id = Column(String(50), unique=True)
    business_unit = Column(String(200))
    office_location = Column(String(150), default="Paris, France (HQ)")
    role = Column(SAEnum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)  # Admin must approve
    credits = Column(Integer, default=20)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    reports = relationship("Report", back_populates="user", lazy="selectin")
    credit_transactions = relationship("CreditTransaction", back_populates="user", lazy="selectin")
    credit_requests = relationship("CreditRequest", back_populates="user", lazy="selectin")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Company(Base):
    """Cache of analyzed companies to avoid redundant API calls."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), unique=True, index=True)
    country = Column(String(100))
    sector = Column(String(150))
    founded_year = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    reports = relationship("Report", back_populates="company", lazy="selectin")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    request_code = Column(String(50), unique=True, index=True)

    # Relations
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Status
    status = Column(SAEnum(ReportStatus), default=ReportStatus.PENDING)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.UNKNOWN)
    vulnerability_score = Column(Float, nullable=True)

    # Report content (JSON stored as text)
    raw_data_json = Column(Text)          # Silobreak raw triage output
    legal_analysis_json = Column(Text)    # Legal & Integrity Agent
    executive_analysis_json = Column(Text) # Executive & Reputation Agent
    operations_analysis_json = Column(Text) # Operations & Finance Agent
    evidence_json = Column(Text)           # Evidence Agent validation
    final_report_json = Column(Text)       # Orchestrator final synthesis
    top_issues = Column(Text)              # Comma-separated list of top issues

    # PDF
    pdf_path = Column(String(500))         # Local path to generated PDF

    # Credits
    credits_used = Column(Integer, default=10)

    # Timestamps
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="reports")
    company = relationship("Company", back_populates="reports")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)         # Positive = credit, negative = debit
    transaction_type = Column(SAEnum(CreditTransactionType))
    description = Column(String(500))
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="credit_transactions")


class CreditRequest(Base):
    __tablename__ = "credit_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_requested = Column(Integer, nullable=False)
    justification = Column(Text)
    status = Column(SAEnum(CreditRequestStatus), default=CreditRequestStatus.PENDING)
    admin_note = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="credit_requests",
                        foreign_keys=[user_id])


# ---- Dependency --------------------------------------------------------
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---- Init DB -----------------------------------------------------------
async def init_db():
    """Create all tables and seed admin user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed admin
    from .auth import get_password_hash
    from .config import settings
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        existing_admin = result.scalar_one_or_none()

        if not existing_admin:
            admin = User(
                first_name="Platform",
                last_name="Administrator",
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                job_title="System Administrator",
                internal_id="ADMIN-0001",
                business_unit="Technology & Operations",
                role=UserRole.ADMIN,
                is_active=True,
                is_approved=True,
                credits=9999,
            )
            session.add(admin)
            await session.commit()
            print(f"✅ Admin user created: {settings.ADMIN_EMAIL}")

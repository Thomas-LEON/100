# ============================================================
# backend/schemas.py — Pydantic Request & Response Models
# ============================================================
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, field_validator


# ============================================================
# AUTH
# ============================================================
class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    job_title: Optional[str] = None
    internal_id: Optional[str] = None
    business_unit: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    username: str   # email or internal_id
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ============================================================
# USER
# ============================================================
class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str]
    internal_id: Optional[str]
    business_unit: Optional[str]
    office_location: Optional[str]
    role: str
    credits: int
    is_approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    job_title: Optional[str] = None
    business_unit: Optional[str] = None
    office_location: Optional[str] = None


class UserAdminUpdate(BaseModel):
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None
    credits: Optional[int] = None
    role: Optional[str] = None


# ============================================================
# COMPANY
# ============================================================
class CompanyOut(BaseModel):
    id: int
    name: str
    domain: Optional[str]
    country: Optional[str]
    sector: Optional[str]
    founded_year: Optional[int]

    model_config = {"from_attributes": True}


# ============================================================
# REPORT
# ============================================================
class ReportRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    force_regenerate: bool = False


class ReportOut(BaseModel):
    id: int
    request_code: str
    status: str
    risk_level: str
    vulnerability_score: Optional[float]
    top_issues: Optional[str]
    credits_used: int
    requested_at: datetime
    completed_at: Optional[datetime]
    pdf_path: Optional[str]
    company: Optional[CompanyOut]
    user: Optional[UserOut]

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    id: int
    request_code: str
    status: str
    risk_level: str
    vulnerability_score: Optional[float]
    top_issues: Optional[str]
    credits_used: int
    requested_at: datetime
    completed_at: Optional[datetime]
    company_name: str
    company_domain: Optional[str]
    user_name: str

    model_config = {"from_attributes": True}


class ReportDetail(ReportOut):
    """Full report including agent analyses."""
    legal_analysis: Optional[Any] = None
    executive_analysis: Optional[Any] = None
    operations_analysis: Optional[Any] = None
    evidence_summary: Optional[Any] = None
    final_synthesis: Optional[Any] = None


class ReportCheckResponse(BaseModel):
    """Returned when checking if a report exists for a company."""
    has_recent_report: bool
    report: Optional[ReportOut] = None
    days_old: Optional[int] = None
    is_valid: bool = False   # True if within 14-day window


# ============================================================
# CREDITS
# ============================================================
class CreditTransactionOut(BaseModel):
    id: int
    amount: int
    transaction_type: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CreditRequestCreate(BaseModel):
    amount_requested: int
    justification: str

    @field_validator("amount_requested")
    @classmethod
    def valid_amount(cls, v):
        if v <= 0 or v > 500:
            raise ValueError("Credit amount must be between 1 and 500")
        return v


class CreditRequestOut(BaseModel):
    id: int
    amount_requested: int
    justification: str
    status: str
    admin_note: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    user: Optional[UserOut]

    model_config = {"from_attributes": True}


class CreditRequestReview(BaseModel):
    approved: bool
    admin_note: Optional[str] = None


# ============================================================
# DASHBOARD / STATS
# ============================================================
class DashboardStats(BaseModel):
    total_companies_analyzed: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    total_reports_all: int
    my_credits: int
    recent_reports: List[ReportListItem]
    monthly_trend: List[dict]
    top_sectors: List[dict]
    vulnerability_breakdown: dict


# ============================================================
# ADMIN
# ============================================================
class AuditTrailItem(BaseModel):
    id: int
    request_code: str
    first_name: str
    last_name: str
    internal_id: Optional[str]
    email: str
    business_unit: Optional[str]
    job_title: Optional[str]
    office_location: Optional[str]
    company_name: str
    vulnerability_score: Optional[float]
    risk_level: str
    credits_used: int
    credits_remaining: int
    status: str
    requested_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# GENERIC
# ============================================================
class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

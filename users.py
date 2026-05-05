# ============================================================
# backend/routers/users.py — User Profile + Credits Endpoints
# ============================================================
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..database import get_db, User, CreditTransaction, CreditRequest, CreditRequestStatus, CreditTransactionType
from ..auth import get_current_user, get_current_admin
from ..schemas import (
    UserOut, UserUpdateRequest, UserAdminUpdate,
    CreditTransactionOut, CreditRequestCreate, CreditRequestOut, CreditRequestReview,
    MessageResponse, PaginatedResponse,
)

router = APIRouter(prefix="/api/users", tags=["Users"])


# ── GET /api/users/me ────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
async def get_profile(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


# ── PUT /api/users/me ────────────────────────────────────────────────────
@router.put("/me", response_model=UserOut)
async def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)
    return UserOut.model_validate(current_user)


# ── GET /api/users/me/credits ────────────────────────────────────────────
@router.get("/me/credits")
async def get_credits(current_user: User = Depends(get_current_user)):
    return {"credits": current_user.credits}


# ── GET /api/users/me/transactions ───────────────────────────────────────
@router.get("/me/transactions", response_model=list[CreditTransactionOut])
async def get_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
        .order_by(desc(CreditTransaction.created_at))
        .limit(20)
    )
    return [CreditTransactionOut.model_validate(t) for t in result.scalars()]


# ── POST /api/users/me/credit-requests ───────────────────────────────────
@router.post("/me/credit-requests", response_model=MessageResponse, status_code=201)
async def request_credits(
    payload: CreditRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req = CreditRequest(
        user_id=current_user.id,
        amount_requested=payload.amount_requested,
        justification=payload.justification,
        status=CreditRequestStatus.PENDING,
    )
    db.add(req)
    await db.commit()
    return MessageResponse(
        message=f"Credit request for {payload.amount_requested} credits submitted. "
                "An administrator will review within 24 business hours."
    )


# ── GET /api/users/me/credit-requests ────────────────────────────────────
@router.get("/me/credit-requests", response_model=list[CreditRequestOut])
async def get_my_credit_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditRequest)
        .where(CreditRequest.user_id == current_user.id)
        .order_by(desc(CreditRequest.created_at))
    )
    return [CreditRequestOut.model_validate(r) for r in result.scalars()]


# ============================================================
# backend/routers/dashboard.py — Dashboard Stats
# ============================================================
from fastapi import APIRouter as _APIRouter
from sqlalchemy import func as _func

dashboard_router = _APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@dashboard_router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from ..database import Report, Company, RiskLevel, ReportStatus
    from sqlalchemy import select as _select, desc as _desc

    # BU filter — admins see all, users see their BU
    bu_filter = current_user.business_unit

    # Total companies analyzed in BU
    q_companies = (
        _select(_func.count(_func.distinct(Report.company_id)))
        .join(User, Report.user_id == User.id)
        .where(Report.status == ReportStatus.COMPLETED)
    )
    if current_user.role.value != "admin":
        q_companies = q_companies.where(User.business_unit == bu_filter)
    total_companies = (await db.execute(q_companies)).scalar() or 0

    # Risk breakdown
    async def count_risk(level: RiskLevel):
        q = (
            _select(_func.count(Report.id))
            .join(User, Report.user_id == User.id)
            .where(Report.status == ReportStatus.COMPLETED)
            .where(Report.risk_level == level)
        )
        if current_user.role.value != "admin":
            q = q.where(User.business_unit == bu_filter)
        return (await db.execute(q)).scalar() or 0

    high_count = await count_risk(RiskLevel.HIGH)
    medium_count = await count_risk(RiskLevel.MEDIUM)
    low_count = await count_risk(RiskLevel.LOW)

    # Total reports (global)
    total_reports = (
        await db.execute(
            _select(_func.count(Report.id)).where(Report.status == ReportStatus.COMPLETED)
        )
    ).scalar() or 0

    # Recent 5 reports (user's BU)
    recent_q = (
        _select(Report)
        .join(Company, Report.company_id == Company.id)
        .join(User, Report.user_id == User.id)
        .where(Report.status == ReportStatus.COMPLETED)
        .order_by(_desc(Report.completed_at))
        .limit(5)
    )
    if current_user.role.value != "admin":
        recent_q = recent_q.where(User.business_unit == bu_filter)
    recent_reports = (await db.execute(recent_q)).scalars().all()

    recent_data = [
        {
            "id": r.id,
            "request_code": r.request_code,
            "company_name": r.company.name if r.company else "Unknown",
            "company_domain": r.company.domain if r.company else None,
            "vulnerability_score": r.vulnerability_score,
            "risk_level": r.risk_level.value,
            "top_issues": r.top_issues,
            "requested_at": r.requested_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "user_name": r.user.full_name if r.user else "Unknown",
        }
        for r in recent_reports
    ]

    # Monthly trend (last 12 months)
    from datetime import timedelta
    trend = []
    now = datetime.now(timezone.utc)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for i in range(11, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        if i > 0:
            month_end = (now.replace(day=1) - timedelta(days=30 * (i - 1))).replace(day=1)
        else:
            month_end = now

        q = (
            _select(_func.count(Report.id))
            .where(Report.status == ReportStatus.COMPLETED)
            .where(Report.completed_at >= month_start)
            .where(Report.completed_at < month_end)
        )
        count = (await db.execute(q)).scalar() or 0

        high_q = q.where(Report.risk_level == RiskLevel.HIGH)
        high_m = (await db.execute(high_q)).scalar() or 0

        trend.append({
            "month": months[month_start.month - 1],
            "year": month_start.year,
            "total": count,
            "high": high_m,
        })

    return {
        "total_companies_analyzed": total_companies,
        "high_risk_count": high_count,
        "medium_risk_count": medium_count,
        "low_risk_count": low_count,
        "total_reports_all": total_reports,
        "my_credits": current_user.credits,
        "recent_reports": recent_data,
        "monthly_trend": trend,
        "vulnerability_breakdown": {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
    }


# ============================================================
# backend/routers/admin.py — Admin Endpoints
# ============================================================
admin_router = _APIRouter(prefix="/api/admin", tags=["Admin"])


@admin_router.get("/users")
async def list_all_users(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as _select
    result = await db.execute(_select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@admin_router.put("/users/{user_id}", response_model=UserOut)
async def admin_update_user(
    user_id: int,
    payload: UserAdminUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as _select
    result = await db.execute(_select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@admin_router.get("/credit-requests")
async def list_credit_requests(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as _select, desc as _desc
    result = await db.execute(
        _select(CreditRequest)
        .order_by(_desc(CreditRequest.created_at))
    )
    requests = result.scalars().all()
    return [CreditRequestOut.model_validate(r) for r in requests]


@admin_router.put("/credit-requests/{request_id}", response_model=MessageResponse)
async def review_credit_request(
    request_id: int,
    payload: CreditRequestReview,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as _select
    result = await db.execute(_select(CreditRequest).where(CreditRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Credit request not found")

    if req.status != CreditRequestStatus.PENDING:
        raise HTTPException(status_code=409, detail="This request has already been reviewed")

    req.status = CreditRequestStatus.APPROVED if payload.approved else CreditRequestStatus.REJECTED
    req.admin_note = payload.admin_note
    req.reviewed_by_id = current_admin.id
    req.reviewed_at = datetime.now(timezone.utc)

    if payload.approved:
        # Credit the user
        user_result = await db.execute(_select(User).where(User.id == req.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.credits += req.amount_requested
            txn = CreditTransaction(
                user_id=user.id,
                amount=req.amount_requested,
                transaction_type=CreditTransactionType.CREDIT,
                description=f"Admin top-up approved — {req.amount_requested} credits (Request #{request_id})",
            )
            db.add(txn)

    await db.commit()
    action = "approved" if payload.approved else "rejected"
    return MessageResponse(message=f"Credit request #{request_id} {action}.")


@admin_router.get("/audit-trail")
async def get_audit_trail(
    page: int = 1,
    page_size: int = 10,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Full audit trail — every request with user info, company, credits."""
    from sqlalchemy import select as _select, desc as _desc, func as _func
    from ..database import Report, Company
    import math

    q = (
        _select(Report)
        .join(Company, Report.company_id == Company.id)
        .join(User, Report.user_id == User.id)
        .order_by(_desc(Report.requested_at))
    )

    total = (await db.execute(_select(_func.count()).select_from(q.subquery()))).scalar()
    q = q.offset((page - 1) * page_size).limit(page_size)
    reports = (await db.execute(q)).scalars().all()

    items = []
    for r in reports:
        user = r.user
        company = r.company
        items.append({
            "id": r.id,
            "request_code": r.request_code,
            "first_name": user.first_name if user else "",
            "last_name": user.last_name if user else "",
            "internal_id": user.internal_id if user else None,
            "email": user.email if user else "",
            "business_unit": user.business_unit if user else None,
            "job_title": user.job_title if user else None,
            "office_location": user.office_location if user else None,
            "company_name": company.name if company else "Unknown",
            "vulnerability_score": r.vulnerability_score,
            "risk_level": r.risk_level.value,
            "credits_used": r.credits_used,
            "credits_remaining": user.credits if user else 0,
            "status": r.status.value,
            "requested_at": r.requested_at.isoformat(),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }

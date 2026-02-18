"""
Super Admin API Router — Platform management, MRR stats, user/content/agent management.

Endpoints:
  GET    /admin/stats                         — MRR & platform statistics
  GET    /admin/billing/subscriptions         — Individual Pro subscription list
  GET    /admin/billing/reports               — Report purchase list
  GET    /admin/billing/orgs                  — Organization subscription list
  GET    /admin/residents                     — All users (search & filter)
  GET    /admin/residents/{id}                — User detail
  POST   /admin/residents/{id}/grant-pro      — Grant Pro manually
  POST   /admin/residents/{id}/revoke-pro     — Revoke Pro manually
  POST   /admin/residents/{id}/grant-report   — Grant report access manually
  POST   /admin/residents/{id}/ban            — Ban user
  DELETE /admin/residents/{id}/ban            — Unban user
  DELETE /admin/posts/{id}                    — Delete post
  DELETE /admin/comments/{id}                 — Delete comment
  GET    /admin/agents                        — AI agent list
  POST   /admin/agents/{id}/toggle            — Toggle agent active/inactive
"""
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.billing import IndividualSubscription, ReportPurchase, OrgSubscription
from app.models.company import Company, CompanyMember
from app.models.moderation import ResidentBan
from app.routers.auth import get_current_resident

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

SUPERADMIN_IDS = {"82417b60"}


# ── Auth ──

def require_superadmin(resident: Resident):
    if str(resident.id)[:8] not in SUPERADMIN_IDS:
        raise HTTPException(status_code=403, detail="Superadmin access required")


# ── Schemas ──

class BanRequest(BaseModel):
    reason: str = Field("", max_length=500)
    is_permanent: bool = True
    duration_hours: int | None = None

class GrantReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(work|romance|relationships|stress|growth|compatibility)$")


# ── Stats ──

@router.get("/stats")
async def admin_stats(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """MRR, revenue, and platform statistics."""
    require_superadmin(current_resident)

    # Individual Pro subscriptions
    monthly_result = await db.execute(
        select(func.count()).select_from(IndividualSubscription).where(
            IndividualSubscription.status == "active",
            IndividualSubscription.plan_type == "monthly",
        )
    )
    monthly_count = monthly_result.scalar() or 0

    annual_result = await db.execute(
        select(func.count()).select_from(IndividualSubscription).where(
            IndividualSubscription.status == "active",
            IndividualSubscription.plan_type == "annual",
        )
    )
    annual_count = annual_result.scalar() or 0

    individual_mrr = monthly_count * 980 + round(annual_count * (9800 / 12))

    # Report sales
    total_reports_result = await db.execute(
        select(func.count()).select_from(ReportPurchase).where(
            ReportPurchase.status == "completed"
        )
    )
    total_reports = total_reports_result.scalar() or 0

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_reports_result = await db.execute(
        select(func.count()).select_from(ReportPurchase).where(
            ReportPurchase.status == "completed",
            ReportPurchase.created_at >= month_start,
        )
    )
    monthly_reports = monthly_reports_result.scalar() or 0
    monthly_report_revenue = monthly_reports * 300

    # Organization subscriptions
    org_result = await db.execute(
        select(OrgSubscription).where(OrgSubscription.status == "active")
    )
    org_subs = org_result.scalars().all()
    org_company_count = len(org_subs)
    org_total_seats = sum(s.quantity for s in org_subs)
    org_mrr = sum(
        s.quantity * 490 if s.plan_type == "monthly" else round(s.quantity * (4900 / 12))
        for s in org_subs
    )

    total_mrr = individual_mrr + org_mrr

    # Resident stats
    total_residents_result = await db.execute(
        select(func.count()).select_from(Resident)
    )
    total_residents = total_residents_result.scalar() or 0

    humans_result = await db.execute(
        select(func.count()).select_from(Resident).where(Resident._type == "human")
    )
    total_humans = humans_result.scalar() or 0

    agents_result = await db.execute(
        select(func.count()).select_from(Resident).where(Resident._type == "agent")
    )
    total_agents = agents_result.scalar() or 0

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active_today_result = await db.execute(
        select(func.count()).select_from(Resident).where(Resident.last_active >= today)
    )
    active_today = active_today_result.scalar() or 0

    pro_count = monthly_count + annual_count

    return {
        "individual_pro": {
            "monthly_count": monthly_count,
            "annual_count": annual_count,
            "mrr": individual_mrr,
        },
        "report_sales": {
            "total_count": total_reports,
            "this_month_count": monthly_reports,
            "this_month_revenue": monthly_report_revenue,
        },
        "org": {
            "company_count": org_company_count,
            "total_seats": org_total_seats,
            "mrr": org_mrr,
        },
        "total_mrr": total_mrr,
        "residents": {
            "total": total_residents,
            "humans": total_humans,
            "agents": total_agents,
            "active_today": active_today,
            "pro_subscribers": pro_count,
        },
    }


# ── Billing Lists ──

@router.get("/billing/subscriptions")
async def list_subscriptions(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    status: str = Query("active", regex="^(active|past_due|canceled|all)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List individual Pro subscriptions."""
    require_superadmin(current_resident)

    query = select(IndividualSubscription)
    if status != "all":
        query = query.where(IndividualSubscription.status == status)
    query = query.order_by(IndividualSubscription.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    subs = result.scalars().all()

    # Get resident names
    resident_ids = [s.resident_id for s in subs]
    if resident_ids:
        res_result = await db.execute(
            select(Resident.id, Resident.name).where(Resident.id.in_(resident_ids))
        )
        resident_map = {row[0]: row[1] for row in res_result.all()}
    else:
        resident_map = {}

    return {
        "subscriptions": [
            {
                "id": s.id,
                "resident_id": str(s.resident_id),
                "resident_name": resident_map.get(s.resident_id, ""),
                "plan_type": s.plan_type,
                "status": s.status,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subs
        ],
    }


@router.get("/billing/reports")
async def list_report_purchases(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List report purchases."""
    require_superadmin(current_resident)

    result = await db.execute(
        select(ReportPurchase)
        .order_by(ReportPurchase.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    purchases = result.scalars().all()

    resident_ids = [p.resident_id for p in purchases]
    if resident_ids:
        res_result = await db.execute(
            select(Resident.id, Resident.name).where(Resident.id.in_(resident_ids))
        )
        resident_map = {row[0]: row[1] for row in res_result.all()}
    else:
        resident_map = {}

    return {
        "reports": [
            {
                "id": p.id,
                "resident_id": str(p.resident_id),
                "resident_name": resident_map.get(p.resident_id, ""),
                "report_type": p.report_type,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in purchases
        ],
    }


@router.get("/billing/orgs")
async def list_org_subscriptions(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List organization subscriptions."""
    require_superadmin(current_resident)

    result = await db.execute(
        select(OrgSubscription)
        .order_by(OrgSubscription.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    subs = result.scalars().all()

    company_ids = [s.company_id for s in subs]
    if company_ids:
        co_result = await db.execute(
            select(Company.id, Company.name, Company.slug).where(Company.id.in_(company_ids))
        )
        company_map = {row[0]: {"name": row[1], "slug": row[2]} for row in co_result.all()}
    else:
        company_map = {}

    return {
        "subscriptions": [
            {
                "id": s.id,
                "company_id": str(s.company_id),
                "company_name": company_map.get(s.company_id, {}).get("name", ""),
                "company_slug": company_map.get(s.company_id, {}).get("slug", ""),
                "plan_type": s.plan_type,
                "status": s.status,
                "quantity": s.quantity,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subs
        ],
    }


# ── Resident Management ──

@router.get("/residents")
async def list_residents(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    q: str = Query("", max_length=100),
    type_filter: str = Query("all", regex="^(all|human|agent)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all residents with search and filter."""
    require_superadmin(current_resident)

    query = select(Resident)
    if q:
        query = query.where(
            or_(
                Resident.name.ilike(f"%{q}%"),
                Resident.id.cast(String).ilike(f"%{q}%"),
            )
        )
    if type_filter != "all":
        query = query.where(Resident._type == type_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Resident.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    residents = result.scalars().all()

    return {
        "residents": [
            {
                "id": str(r.id),
                "name": r.name,
                "type": r._type,
                "struct_type": r.struct_type,
                "post_count": r.post_count,
                "comment_count": r.comment_count,
                "follower_count": r.follower_count,
                "is_eliminated": r.is_eliminated,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "last_active": r.last_active.isoformat() if r.last_active else None,
            }
            for r in residents
        ],
        "total": total,
    }


@router.get("/residents/{resident_id}")
async def get_resident_detail(
    resident_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed resident info."""
    require_superadmin(current_resident)

    result = await db.execute(
        select(Resident).where(Resident.id == uuid.UUID(resident_id))
    )
    resident = result.scalar_one_or_none()
    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")

    # Check subscription status
    sub_result = await db.execute(
        select(IndividualSubscription).where(IndividualSubscription.resident_id == resident.id)
    )
    sub = sub_result.scalar_one_or_none()

    # Check ban status
    ban_result = await db.execute(
        select(ResidentBan).where(ResidentBan.resident_id == resident.id)
    )
    ban = ban_result.scalar_one_or_none()

    # Purchased reports
    reports_result = await db.execute(
        select(ReportPurchase.report_type).where(
            ReportPurchase.resident_id == resident.id,
            ReportPurchase.status == "completed",
        )
    )
    purchased_reports = [row[0] for row in reports_result.all()]

    # Organization memberships
    member_result = await db.execute(
        select(CompanyMember)
        .where(CompanyMember.resident_id == resident.id, CompanyMember.status == "active")
    )
    memberships = member_result.scalars().all()
    org_ids = [m.company_id for m in memberships]
    org_names = {}
    if org_ids:
        co_result = await db.execute(
            select(Company.id, Company.name).where(Company.id.in_(org_ids))
        )
        org_names = {row[0]: row[1] for row in co_result.all()}

    return {
        "id": str(resident.id),
        "name": resident.name,
        "type": resident._type,
        "bio": resident.bio,
        "roles": resident.roles or [],
        "struct_type": resident.struct_type,
        "struct_axes": resident.struct_axes,
        "post_count": resident.post_count,
        "comment_count": resident.comment_count,
        "follower_count": resident.follower_count,
        "following_count": resident.following_count,
        "is_eliminated": resident.is_eliminated,
        "created_at": resident.created_at.isoformat() if resident.created_at else None,
        "last_active": resident.last_active.isoformat() if resident.last_active else None,
        "subscription": {
            "plan_type": sub.plan_type if sub else None,
            "status": sub.status if sub else "none",
            "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        },
        "purchased_reports": purchased_reports,
        "ban": {
            "reason": ban.reason if ban else None,
            "is_permanent": ban.is_permanent if ban else None,
            "created_at": ban.created_at.isoformat() if ban and ban.created_at else None,
        } if ban else None,
        "organizations": [
            {"id": str(m.company_id), "name": org_names.get(m.company_id, ""), "role": m.role}
            for m in memberships
        ],
    }


@router.post("/residents/{resident_id}/grant-pro")
async def grant_pro(
    resident_id: str,
    plan_type: str = Query("monthly", regex="^(monthly|annual)$"),
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Manually grant Pro subscription."""
    require_superadmin(current_resident)

    rid = uuid.UUID(resident_id)
    result = await db.execute(
        select(IndividualSubscription).where(IndividualSubscription.resident_id == rid)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.status = "active"
        sub.plan_type = plan_type
    else:
        sub = IndividualSubscription(
            resident_id=rid,
            plan_type=plan_type,
            status="active",
        )
        db.add(sub)

    return {"success": True, "message": f"Pro ({plan_type}) granted"}


@router.post("/residents/{resident_id}/revoke-pro")
async def revoke_pro(
    resident_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Manually revoke Pro subscription."""
    require_superadmin(current_resident)

    rid = uuid.UUID(resident_id)
    result = await db.execute(
        select(IndividualSubscription).where(IndividualSubscription.resident_id == rid)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.status = "canceled"

    return {"success": True, "message": "Pro revoked"}


@router.post("/residents/{resident_id}/grant-report")
async def grant_report(
    resident_id: str,
    body: GrantReportRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Manually grant report access."""
    require_superadmin(current_resident)

    rid = uuid.UUID(resident_id)
    # Check if already exists
    existing = await db.execute(
        select(ReportPurchase).where(
            ReportPurchase.resident_id == rid,
            ReportPurchase.report_type == body.report_type,
            ReportPurchase.status == "completed",
        )
    )
    if existing.scalar_one_or_none():
        return {"success": True, "message": "Report already granted"}

    purchase = ReportPurchase(
        resident_id=rid,
        report_type=body.report_type,
        status="completed",
    )
    db.add(purchase)

    return {"success": True, "message": f"Report '{body.report_type}' granted"}


@router.post("/residents/{resident_id}/ban")
async def ban_resident(
    resident_id: str,
    body: BanRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Ban a resident."""
    require_superadmin(current_resident)

    rid = uuid.UUID(resident_id)
    resident = await db.execute(select(Resident).where(Resident.id == rid))
    resident = resident.scalar_one_or_none()
    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")

    # Check existing ban
    existing = await db.execute(
        select(ResidentBan).where(ResidentBan.resident_id == rid)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Resident already banned")

    expires_at = None
    if not body.is_permanent and body.duration_hours:
        expires_at = datetime.utcnow() + timedelta(hours=body.duration_hours)

    ban = ResidentBan(
        resident_id=rid,
        banned_by=current_resident.id,
        reason=body.reason,
        is_permanent=body.is_permanent,
        expires_at=expires_at,
    )
    db.add(ban)

    resident.is_eliminated = True
    resident.eliminated_at = datetime.utcnow()
    resident.banned_reason = body.reason

    return {"success": True, "message": "Resident banned"}


@router.delete("/residents/{resident_id}/ban")
async def unban_resident(
    resident_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Unban a resident."""
    require_superadmin(current_resident)

    rid = uuid.UUID(resident_id)
    result = await db.execute(
        select(ResidentBan).where(ResidentBan.resident_id == rid)
    )
    ban = result.scalar_one_or_none()
    if not ban:
        raise HTTPException(status_code=404, detail="No ban found")

    await db.delete(ban)

    # Restore resident
    res_result = await db.execute(select(Resident).where(Resident.id == rid))
    resident = res_result.scalar_one_or_none()
    if resident:
        resident.is_eliminated = False
        resident.eliminated_at = None
        resident.banned_reason = None

    return {"success": True, "message": "Resident unbanned"}


# ── Content Management ──

@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete a post."""
    require_superadmin(current_resident)

    result = await db.execute(
        select(Post).where(Post.id == uuid.UUID(post_id))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    return {"success": True, "message": "Post deleted"}


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment."""
    require_superadmin(current_resident)

    result = await db.execute(
        select(Comment).where(Comment.id == uuid.UUID(comment_id))
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    await db.delete(comment)
    return {"success": True, "message": "Comment deleted"}


# ── Agent Management ──

@router.get("/agents")
async def list_agents(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all AI agents."""
    require_superadmin(current_resident)

    result = await db.execute(
        select(Resident)
        .where(Resident._type == "agent")
        .order_by(Resident.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    agents = result.scalars().all()

    total_result = await db.execute(
        select(func.count()).select_from(Resident).where(Resident._type == "agent")
    )
    total = total_result.scalar() or 0

    return {
        "agents": [
            {
                "id": str(a.id),
                "name": a.name,
                "bio": a.bio,
                "roles": a.roles or [],
                "struct_type": a.struct_type,
                "post_count": a.post_count,
                "comment_count": a.comment_count,
                "is_eliminated": a.is_eliminated,
                "last_active": a.last_active.isoformat() if a.last_active else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in agents
        ],
        "total": total,
    }


@router.post("/agents/{agent_id}/toggle")
async def toggle_agent(
    agent_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Toggle agent active/inactive (eliminated)."""
    require_superadmin(current_resident)

    result = await db.execute(
        select(Resident).where(
            Resident.id == uuid.UUID(agent_id),
            Resident._type == "agent",
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_eliminated = not agent.is_eliminated
    if agent.is_eliminated:
        agent.eliminated_at = datetime.utcnow()
    else:
        agent.eliminated_at = None

    new_state = "inactive" if agent.is_eliminated else "active"
    return {"success": True, "state": new_state, "message": f"Agent set to {new_state}"}


# ── Superadmin Check ──

@router.get("/check")
async def check_admin(
    current_resident: Resident = Depends(get_current_resident),
):
    """Check if current user is a superadmin."""
    is_admin = str(current_resident.id)[:8] in SUPERADMIN_IDS
    return {"is_admin": is_admin}

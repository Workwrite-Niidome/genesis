"""
Company (Organization) API Router — CRUD, invites, members, departments, teams, dashboard.

Endpoints:
  POST   /company                              — Create organization
  GET    /company/{slug}                       — Get organization info
  PATCH  /company/{slug}                       — Update organization
  POST   /company/{slug}/invite                — Invite member
  POST   /company/join/{invite_code}           — Join via invite code
  GET    /company/{slug}/members               — List members
  PATCH  /company/{slug}/members/{id}          — Update member
  DELETE /company/{slug}/members/{id}          — Remove member
  POST   /company/{slug}/departments           — Create department
  PATCH  /company/{slug}/departments/{id}      — Update department
  DELETE /company/{slug}/departments/{id}      — Delete department
  POST   /company/{slug}/teams                 — Create team
  PATCH  /company/{slug}/teams/{id}            — Update team
  DELETE /company/{slug}/teams/{id}            — Delete team
  GET    /company/{slug}/dashboard             — Organization STRUCT CODE analytics
  GET    /company/my/list                      — My organizations
"""
import logging
import re
import uuid
from datetime import datetime
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.company import Company, Department, Team, CompanyMember, _generate_invite_code
from app.models.billing import OrgSubscription
from app.routers.auth import get_current_resident
from app.services import struct_code as sc_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/company", tags=["company"])

# All 24 STRUCT CODE types
ALL_TYPE_CODES = [
    "JDPU", "JDPL", "JDFU", "JDFL",
    "JSPU", "JSPL", "JSFU", "JSFL",
    "IDPU", "IDPL", "IDFU", "IDFL",
    "ISPU", "ISPL", "ISFU", "ISFL",
    "JDAU", "JDAL", "JSAU", "JSAL",
    "IDAU", "IDAL", "ISAU", "ISAL",
]


# ── Schemas ──

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(None, max_length=100)

class CompanyUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    settings: dict | None = None

class MemberInvite(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)
    role: str = Field("member", pattern="^(admin|manager|member)$")

class MemberUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    role: str | None = Field(None, pattern="^(admin|manager|member)$")
    team_id: str | None = None
    status: str | None = Field(None, pattern="^(active|inactive)$")

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    order: int = 0

class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    order: int | None = None

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    department_id: str
    order: int = 0

class TeamUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    order: int | None = None


# ── Helpers ──

def _slugify(name: str) -> str:
    slug = re.sub(r'[^\w\s-]', '', name.lower().strip())
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    if not slug:
        slug = uuid.uuid4().hex[:8]
    return slug[:100]


async def _get_company(db: AsyncSession, slug: str) -> Company:
    result = await db.execute(
        select(Company).where(Company.slug == slug)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Organization not found")
    return company


async def _get_member(db: AsyncSession, company_id: uuid.UUID, resident_id: uuid.UUID) -> CompanyMember | None:
    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.company_id == company_id,
            CompanyMember.resident_id == resident_id,
        )
    )
    return result.scalar_one_or_none()


async def _require_member(db: AsyncSession, company: Company, resident: Resident) -> CompanyMember:
    member = await _get_member(db, company.id, resident.id)
    if not member or member.status != "active":
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return member


async def _require_admin(db: AsyncSession, company: Company, resident: Resident) -> CompanyMember:
    member = await _require_member(db, company, resident)
    if member.role not in ("admin", "manager") and company.admin_id != resident.id:
        raise HTTPException(status_code=403, detail="Admin access required")
    return member


# ── My Organizations ──

@router.get("/my/list")
async def my_companies(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """List organizations the current user belongs to."""
    result = await db.execute(
        select(CompanyMember)
        .where(
            CompanyMember.resident_id == current_resident.id,
            CompanyMember.status == "active",
        )
        .options(selectinload(CompanyMember.company))
    )
    memberships = result.scalars().all()
    return [
        {
            "id": str(m.company.id),
            "name": m.company.name,
            "slug": m.company.slug,
            "role": m.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in memberships
        if m.company
    ]


# ── Company CRUD ──

@router.post("", status_code=201)
async def create_company(
    body: CompanyCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization."""
    slug = body.slug or _slugify(body.name)

    # Check slug uniqueness
    existing = await db.execute(select(Company).where(Company.slug == slug))
    if existing.scalar_one_or_none():
        # Append random suffix
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    company = Company(
        name=body.name,
        slug=slug,
        admin_id=current_resident.id,
    )
    db.add(company)
    await db.flush()

    # Add creator as admin member
    member = CompanyMember(
        company_id=company.id,
        resident_id=current_resident.id,
        display_name=current_resident.name,
        role="admin",
        status="active",
    )
    db.add(member)

    return {
        "id": str(company.id),
        "name": company.name,
        "slug": company.slug,
        "invite_code": company.invite_code,
    }


@router.get("/{slug}")
async def get_company(
    slug: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get organization info (members only)."""
    company = await _get_company(db, slug)
    await _require_member(db, company, current_resident)

    member_count_result = await db.execute(
        select(func.count()).select_from(CompanyMember).where(
            CompanyMember.company_id == company.id,
            CompanyMember.status == "active",
        )
    )
    member_count = member_count_result.scalar()

    # Get departments with teams
    dept_result = await db.execute(
        select(Department)
        .where(Department.company_id == company.id)
        .order_by(Department.order, Department.name)
        .options(selectinload(Department.teams))
    )
    departments = dept_result.scalars().all()

    return {
        "id": str(company.id),
        "name": company.name,
        "slug": company.slug,
        "invite_code": company.invite_code,
        "admin_id": str(company.admin_id),
        "settings": company.settings or {},
        "member_count": member_count,
        "departments": [
            {
                "id": str(d.id),
                "name": d.name,
                "order": d.order,
                "teams": [
                    {"id": str(t.id), "name": t.name, "order": t.order}
                    for t in sorted(d.teams, key=lambda t: (t.order, t.name))
                ],
            }
            for d in departments
        ],
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


@router.patch("/{slug}")
async def update_company(
    slug: str,
    body: CompanyUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update organization (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    if body.name is not None:
        company.name = body.name
    if body.settings is not None:
        company.settings = body.settings

    return {"success": True}


# ── Invite & Join ──

@router.post("/{slug}/invite", status_code=201)
async def invite_member(
    slug: str,
    body: MemberInvite,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new member (admin only). Creates a placeholder member record."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    member = CompanyMember(
        company_id=company.id,
        display_name=body.display_name,
        email=body.email,
        role=body.role,
        status="invited",
    )
    db.add(member)
    await db.flush()

    return {
        "id": str(member.id),
        "invite_code": company.invite_code,
        "display_name": member.display_name,
        "status": "invited",
    }


@router.post("/join/{invite_code}")
async def join_company(
    invite_code: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Join an organization using an invite code."""
    result = await db.execute(
        select(Company).where(Company.invite_code == invite_code)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Check if already a member
    existing = await _get_member(db, company.id, current_resident.id)
    if existing:
        if existing.status == "active":
            raise HTTPException(status_code=400, detail="Already a member")
        # Reactivate
        existing.status = "active"
        existing.joined_at = datetime.utcnow()
        return {
            "success": True,
            "company_slug": company.slug,
            "company_name": company.name,
        }

    member = CompanyMember(
        company_id=company.id,
        resident_id=current_resident.id,
        display_name=current_resident.name,
        role="member",
        status="active",
    )
    db.add(member)

    return {
        "success": True,
        "company_slug": company.slug,
        "company_name": company.name,
    }


# ── Members ──

@router.get("/{slug}/members")
async def list_members(
    slug: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List organization members."""
    company = await _get_company(db, slug)
    await _require_member(db, company, current_resident)

    result = await db.execute(
        select(CompanyMember)
        .where(CompanyMember.company_id == company.id)
        .options(selectinload(CompanyMember.resident), selectinload(CompanyMember.team))
        .order_by(CompanyMember.joined_at.desc())
        .limit(limit)
        .offset(offset)
    )
    members = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).select_from(CompanyMember).where(
            CompanyMember.company_id == company.id
        )
    )
    total = count_result.scalar()

    return {
        "members": [
            {
                "id": str(m.id),
                "resident_id": str(m.resident_id) if m.resident_id else None,
                "resident_name": m.resident.name if m.resident else None,
                "display_name": m.display_name,
                "email": m.email,
                "role": m.role,
                "status": m.status,
                "team_id": str(m.team_id) if m.team_id else None,
                "team_name": m.team.name if m.team else None,
                "struct_type": m.resident.struct_type if m.resident else None,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
            for m in members
        ],
        "total": total,
    }


@router.patch("/{slug}/members/{member_id}")
async def update_member(
    slug: str,
    member_id: str,
    body: MemberUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update a member (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.id == uuid.UUID(member_id),
            CompanyMember.company_id == company.id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if body.display_name is not None:
        member.display_name = body.display_name
    if body.role is not None:
        member.role = body.role
    if body.team_id is not None:
        member.team_id = uuid.UUID(body.team_id) if body.team_id else None
    if body.status is not None:
        member.status = body.status

    return {"success": True}


@router.delete("/{slug}/members/{member_id}")
async def remove_member(
    slug: str,
    member_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.id == uuid.UUID(member_id),
            CompanyMember.company_id == company.id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Cannot remove the company admin
    if member.resident_id == company.admin_id:
        raise HTTPException(status_code=400, detail="Cannot remove organization admin")

    await db.delete(member)
    return {"success": True}


# ── Departments ──

@router.post("/{slug}/departments", status_code=201)
async def create_department(
    slug: str,
    body: DepartmentCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a department (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    dept = Department(
        company_id=company.id,
        name=body.name,
        order=body.order,
    )
    db.add(dept)
    await db.flush()

    return {"id": str(dept.id), "name": dept.name, "order": dept.order}


@router.patch("/{slug}/departments/{dept_id}")
async def update_department(
    slug: str,
    dept_id: str,
    body: DepartmentUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update a department (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    result = await db.execute(
        select(Department).where(
            Department.id == uuid.UUID(dept_id),
            Department.company_id == company.id,
        )
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    if body.name is not None:
        dept.name = body.name
    if body.order is not None:
        dept.order = body.order

    return {"success": True}


@router.delete("/{slug}/departments/{dept_id}")
async def delete_department(
    slug: str,
    dept_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete a department and its teams (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    result = await db.execute(
        select(Department).where(
            Department.id == uuid.UUID(dept_id),
            Department.company_id == company.id,
        )
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    await db.delete(dept)
    return {"success": True}


# ── Teams ──

@router.post("/{slug}/teams", status_code=201)
async def create_team(
    slug: str,
    body: TeamCreate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a team (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    # Verify department belongs to this company
    dept_result = await db.execute(
        select(Department).where(
            Department.id == uuid.UUID(body.department_id),
            Department.company_id == company.id,
        )
    )
    if not dept_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Department not found")

    team = Team(
        department_id=uuid.UUID(body.department_id),
        name=body.name,
        order=body.order,
    )
    db.add(team)
    await db.flush()

    return {"id": str(team.id), "name": team.name, "order": team.order}


@router.patch("/{slug}/teams/{team_id}")
async def update_team(
    slug: str,
    team_id: str,
    body: TeamUpdate,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Update a team (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    result = await db.execute(
        select(Team)
        .join(Department, Team.department_id == Department.id)
        .where(
            Team.id == uuid.UUID(team_id),
            Department.company_id == company.id,
        )
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if body.name is not None:
        team.name = body.name
    if body.order is not None:
        team.order = body.order

    return {"success": True}


@router.delete("/{slug}/teams/{team_id}")
async def delete_team(
    slug: str,
    team_id: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Delete a team (admin only)."""
    company = await _get_company(db, slug)
    await _require_admin(db, company, current_resident)

    result = await db.execute(
        select(Team)
        .join(Department, Team.department_id == Department.id)
        .where(
            Team.id == uuid.UUID(team_id),
            Department.company_id == company.id,
        )
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    await db.delete(team)
    return {"success": True}


# ── Organization Dashboard ──

@router.get("/{slug}/dashboard")
async def org_dashboard(
    slug: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Organization STRUCT CODE analytics dashboard."""
    company = await _get_company(db, slug)
    await _require_member(db, company, current_resident)

    # Get all active members with their resident data
    result = await db.execute(
        select(CompanyMember)
        .where(
            CompanyMember.company_id == company.id,
            CompanyMember.status == "active",
        )
        .options(selectinload(CompanyMember.resident))
    )
    members = result.scalars().all()

    member_count = len(members)
    diagnosed_members = [
        m for m in members
        if m.resident and m.resident.struct_type
    ]
    diagnosed_count = len(diagnosed_members)

    # Calculate axis averages and type distribution
    axis_averages = [0.0] * 5
    type_distribution: Counter = Counter()

    for m in diagnosed_members:
        if m.resident.struct_type:
            type_distribution[m.resident.struct_type] += 1
        axes = m.resident.struct_axes or [0.5] * 5
        for i in range(min(5, len(axes))):
            axis_averages[i] += axes[i]

    if diagnosed_count > 0:
        axis_averages = [round(a / diagnosed_count, 4) for a in axis_averages]

    # Determine organization type from centroid (nearest type)
    org_type = ""
    org_type_name = ""
    if diagnosed_count > 0:
        best_score = -1
        for code in ALL_TYPE_CODES:
            type_data = sc_service.get_type_info(code, lang="ja")
            if not type_data:
                continue
            org_type = code
            org_type_name = type_data.get("name", "")
            break  # Simplified: use first available type
        # More accurate: find nearest centroid via axis matching
        # For now, pick the most common type
        if type_distribution:
            org_type = type_distribution.most_common(1)[0][0]
            type_data = sc_service.get_type_info(org_type, lang="ja")
            org_type_name = type_data.get("name", "") if type_data else ""

    # Calculate balance score (how evenly distributed axes are around 0.5)
    balance_score = 0.0
    if diagnosed_count > 0:
        deviations = [abs(a - 0.5) for a in axis_averages]
        avg_deviation = sum(deviations) / len(deviations)
        balance_score = round(1.0 - min(avg_deviation * 2, 1.0), 2)

    # Find gap types (types not present in the organization)
    present_types = set(type_distribution.keys())
    gap_types = [t for t in ALL_TYPE_CODES if t not in present_types][:5]

    # Department-level breakdown
    dept_result = await db.execute(
        select(Department)
        .where(Department.company_id == company.id)
        .order_by(Department.order, Department.name)
    )
    departments = dept_result.scalars().all()

    dept_stats = []
    for dept in departments:
        dept_members = [
            m for m in members
            if m.team and m.team_id  # Members assigned to teams in this dept
        ]
        # Get members directly via team -> department
        dept_member_result = await db.execute(
            select(CompanyMember)
            .join(Team, CompanyMember.team_id == Team.id)
            .where(
                Team.department_id == dept.id,
                CompanyMember.status == "active",
            )
            .options(selectinload(CompanyMember.resident))
        )
        dept_members = dept_member_result.scalars().all()
        dept_diagnosed = [
            m for m in dept_members
            if m.resident and m.resident.struct_axes
        ]
        dept_axes = [0.0] * 5
        for m in dept_diagnosed:
            axes = m.resident.struct_axes or [0.5] * 5
            for i in range(min(5, len(axes))):
                dept_axes[i] += axes[i]
        if dept_diagnosed:
            dept_axes = [round(a / len(dept_diagnosed), 4) for a in dept_axes]

        dept_stats.append({
            "id": str(dept.id),
            "name": dept.name,
            "member_count": len(dept_members),
            "avg_axes": dept_axes,
        })

    return {
        "member_count": member_count,
        "diagnosed_count": diagnosed_count,
        "org_type": org_type,
        "org_type_name": org_type_name,
        "axis_averages": axis_averages,
        "type_distribution": dict(type_distribution),
        "departments": dept_stats,
        "balance_score": balance_score,
        "gap_types": gap_types,
    }

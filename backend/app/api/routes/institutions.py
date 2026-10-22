from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import require_roles, get_current_user
from app.models.user import User
from app.models.institution import Institution, Region
from app.schemas.institution import (
    InstitutionCreateRequest, InstitutionUpdateRequest, InstitutionDetailResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/institutions", tags=["institutions"])

INSTITUTION_ROLES = ("institution_head", "institution_applicant", "institution_viewer")
REGIONAL_ROLES = ("regional_officer", "regional_coordinator")
ADMIN_ROLES = ("system_admin", "bureau_officer", "competent_authority", "scrutiny_officer")


def _enrich_institution(inst: Institution, user_count: int = 0) -> InstitutionDetailResponse:
    return InstitutionDetailResponse(
        id=inst.id,
        pid=inst.pid,
        name=inst.name,
        institution_type=inst.institution_type,
        region_id=inst.region_id,
        region_name=inst.region.name if inst.region else None,
        state=inst.state,
        city=inst.city,
        address=inst.address,
        pincode=inst.pincode,
        contact_email=inst.contact_email,
        contact_phone=inst.contact_phone,
        established_year=inst.established_year,
        website=inst.website,
        created_at=inst.created_at,
        updated_at=inst.updated_at,
        user_count=user_count,
    )


@router.get("", response_model=PaginatedResponse)
async def list_institutions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    region_id: UUID | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Institution)
    count_query = select(func.count()).select_from(Institution)

    # Institution-scoped isolation
    if current_user.role in INSTITUTION_ROLES:
        if not current_user.institution_id:
            return PaginatedResponse(items=[], total=0, page=1, page_size=page_size, pages=0)
        query = query.where(Institution.id == current_user.institution_id)
        count_query = count_query.where(Institution.id == current_user.institution_id)
    elif current_user.role in REGIONAL_ROLES:
        if current_user.region_id:
            query = query.where(Institution.region_id == current_user.region_id)
            count_query = count_query.where(Institution.region_id == current_user.region_id)

    if region_id:
        query = query.where(Institution.region_id == region_id)
        count_query = count_query.where(Institution.region_id == region_id)
    if search:
        pattern = f"%{search}%"
        query = query.where(Institution.name.ilike(pattern))
        count_query = count_query.where(Institution.name.ilike(pattern))

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Institution.name).offset(offset).limit(page_size)
    )
    institutions = result.scalars().all()

    items = []
    for inst in institutions:
        uc = await db.execute(
            select(func.count()).select_from(User).where(User.institution_id == inst.id)
        )
        items.append(_enrich_institution(inst, uc.scalar() or 0))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/regions", response_model=list)
async def list_regions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.schemas.common import RegionResponse
    result = await db.execute(select(Region).order_by(Region.name))
    return [RegionResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/{institution_id}", response_model=InstitutionDetailResponse)
async def get_institution(
    institution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Institution users can only view their own institution
    if current_user.role in INSTITUTION_ROLES and current_user.institution_id != institution_id:
        raise HTTPException(status_code=403, detail="Access denied to this institution")

    # Regional users can only view institutions in their region
    result = await db.execute(select(Institution).where(Institution.id == institution_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    if current_user.role in REGIONAL_ROLES and current_user.region_id and inst.region_id != current_user.region_id:
        raise HTTPException(status_code=403, detail="Access denied to this institution")

    uc = await db.execute(
        select(func.count()).select_from(User).where(User.institution_id == inst.id)
    )
    return _enrich_institution(inst, uc.scalar() or 0)


@router.post("", response_model=InstitutionDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_institution(
    request: InstitutionCreateRequest,
    current_user: User = Depends(require_roles("system_admin", "bureau_officer")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Institution).where(Institution.pid == request.pid))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Institution PID already exists")

    reg = await db.execute(select(Region).where(Region.id == request.region_id))
    if not reg.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Region not found")

    inst = Institution(**request.model_dump())
    db.add(inst)
    await db.flush()
    await db.refresh(inst)

    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="INSTITUTION_CREATED",
        entity_type="Institution",
        entity_id=inst.id,
        changes={"pid": inst.pid, "name": inst.name},
    )

    return _enrich_institution(inst)


@router.patch("/{institution_id}", response_model=InstitutionDetailResponse)
async def update_institution(
    institution_id: UUID,
    request: InstitutionUpdateRequest,
    current_user: User = Depends(require_roles("system_admin", "bureau_officer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Institution).where(Institution.id == institution_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    changes = {}
    for field, value in request.model_dump(exclude_unset=True).items():
        old = getattr(inst, field)
        if old != value:
            changes[field] = {"old": old, "new": value}
            setattr(inst, field, value)

    await db.flush()
    await db.refresh(inst)

    if changes:
        await log_audit_event(
            db,
            actor_id=current_user.id,
            actor_role=current_user.role,
            action="INSTITUTION_UPDATED",
            entity_type="Institution",
            entity_id=inst.id,
            changes=changes,
        )

    uc = await db.execute(
        select(func.count()).select_from(User).where(User.institution_id == inst.id)
    )
    return _enrich_institution(inst, uc.scalar() or 0)

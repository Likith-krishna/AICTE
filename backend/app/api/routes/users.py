from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.security import require_roles, hash_password, get_current_user
from app.models.user import User, Role
from app.models.institution import Institution, Region
from app.schemas.user import (
    UserCreateRequest, UserUpdateRequest, UserDetailResponse,
    UserListParams, RoleResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/users", tags=["users"])

from app.core.roles import ALL_ROLES

# Must match the seeded ``roles`` table (single source: app/core/roles.py).
VALID_ROLES = sorted(ALL_ROLES)


def _enrich_user(user: User) -> UserDetailResponse:
    inst_name = user.institution.name if user.institution else None
    region_name = None
    if user.institution and user.institution.region:
        region_name = user.institution.region.name
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        institution_id=user.institution_id,
        region_id=user.region_id,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        institution_name=inst_name,
        region_name=region_name,
    )


@router.get("", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = None,
    institution_id: UUID | None = None,
    region_id: UUID | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    current_user: User = Depends(require_roles("system_admin", "bureau_officer")),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    count_query = select(func.count()).select_from(User)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if institution_id:
        query = query.where(User.institution_id == institution_id)
        count_query = count_query.where(User.institution_id == institution_id)
    if region_id:
        query = query.where(User.region_id == region_id)
        count_query = count_query.where(User.region_id == region_id)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    if search:
        pattern = f"%{search}%"
        filt = or_(User.full_name.ilike(pattern), User.email.ilike(pattern))
        query = query.where(filt)
        count_query = count_query.where(filt)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return PaginatedResponse(
        items=[_enrich_user(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Role).where(Role.is_active == True).order_by(Role.name))
    return [RoleResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_roles("system_admin", "bureau_officer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _enrich_user(user)


@router.post("", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_roles("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    if request.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")

    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    if request.institution_id:
        inst = await db.execute(select(Institution).where(Institution.id == request.institution_id))
        if not inst.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Institution not found")

    if request.region_id:
        reg = await db.execute(select(Region).where(Region.id == request.region_id))
        if not reg.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Region not found")

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
        institution_id=request.institution_id,
        region_id=request.region_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="USER_CREATED",
        entity_type="User",
        entity_id=user.id,
        changes={"email": user.email, "role": user.role},
    )

    return _enrich_user(user)


@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: User = Depends(require_roles("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}
    if request.full_name is not None:
        changes["full_name"] = {"old": user.full_name, "new": request.full_name}
        user.full_name = request.full_name
    if request.role is not None:
        if request.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
        changes["role"] = {"old": user.role, "new": request.role}
        user.role = request.role
    if request.institution_id is not None:
        user.institution_id = request.institution_id
    if request.region_id is not None:
        user.region_id = request.region_id
    if request.is_active is not None:
        changes["is_active"] = {"old": user.is_active, "new": request.is_active}
        user.is_active = request.is_active

    await db.flush()
    await db.refresh(user)

    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="USER_UPDATED",
        entity_type="User",
        entity_id=user.id,
        changes=changes,
    )

    return _enrich_user(user)


@router.patch("/{user_id}/deactivate", response_model=UserDetailResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_roles("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.flush()
    await db.refresh(user)

    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="USER_DEACTIVATED",
        entity_type="User",
        entity_id=user.id,
    )

    return _enrich_user(user)

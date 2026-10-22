from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user, require_roles
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, UserCreate
from app.core.roles import ALL_ROLES
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserCreate,
    current_user: User = Depends(require_roles("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    if request.role not in ALL_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role: {request.role}")
    if not (8 <= len(request.password) <= 72):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be 8-72 characters")

    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

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
        changes={"email": user.email, "role": user.role, "via": "auth/register"},
    )
    return UserResponse.model_validate(user)

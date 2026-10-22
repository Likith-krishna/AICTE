from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserListParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    role: str | None = None
    institution_id: UUID | None = None
    region_id: UUID | None = None
    is_active: bool | None = None
    search: str | None = None


class UserCreateRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=300)
    role: str
    institution_id: UUID | None = None
    region_id: UUID | None = None


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=300)
    role: str | None = None
    institution_id: UUID | None = None
    region_id: UUID | None = None
    is_active: bool | None = None


class UserDetailResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    institution_id: UUID | None = None
    region_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    institution_name: str | None = None
    region_name: str | None = None

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class InstitutionCreateRequest(BaseModel):
    pid: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=500)
    institution_type: str = "private"
    region_id: UUID
    state: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=200)
    address: str | None = None
    pincode: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    established_year: int | None = None
    website: str | None = None


class InstitutionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    institution_type: str | None = None
    state: str | None = None
    city: str | None = None
    address: str | None = None
    pincode: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website: str | None = None


class InstitutionDetailResponse(BaseModel):
    id: UUID
    pid: str
    name: str
    institution_type: str
    region_id: UUID
    region_name: str | None = None
    state: str
    city: str
    address: str | None = None
    pincode: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    established_year: int | None = None
    website: str | None = None
    created_at: datetime
    updated_at: datetime
    user_count: int = 0

    model_config = {"from_attributes": True}

from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class RegionResponse(BaseModel):
    id: UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class InstitutionResponse(BaseModel):
    id: UUID
    pid: str
    name: str
    institution_type: str
    state: str
    city: str
    region_id: UUID

    model_config = {"from_attributes": True}


class AcademicYearResponse(BaseModel):
    id: UUID
    year_label: str
    start_date: date
    end_date: date
    is_current: bool

    model_config = {"from_attributes": True}


class AuditEventResponse(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: UUID | None
    changes: dict | None
    occurred_at: datetime

    model_config = {"from_attributes": True}

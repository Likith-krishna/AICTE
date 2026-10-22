from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ApplicationCreateRequest(BaseModel):
    category_id: UUID
    academic_year_id: UUID
    form_data: dict[str, Any] | None = None


class ApplicationUpdateRequest(BaseModel):
    form_data: dict[str, Any]
    expected_version: int = Field(ge=1)


class TransitionRequest(BaseModel):
    to_stage: str = Field(min_length=1, max_length=50)
    remarks: str | None = Field(None, max_length=4000)
    expected_version: int = Field(ge=1)


class VersionedRequest(BaseModel):
    expected_version: int = Field(ge=1)
    remarks: str | None = Field(None, max_length=1000)


class CategoryResponse(BaseModel):
    id: UUID
    code: str
    name: str
    processing_category: int
    requires_self_disclosure: bool
    requires_scrutiny: bool
    requires_evc: bool
    sac_shc_applicable: str
    route_type: str
    workflow_name: str


class AcademicYearOption(BaseModel):
    id: UUID
    year_label: str
    start_date: date
    end_date: date
    is_current: bool

    model_config = {"from_attributes": True}


class ApplicationListItem(BaseModel):
    id: UUID
    reference_number: str
    institution_id: UUID
    institution_name: str
    category_code: str
    category_name: str
    route_type: str
    academic_year: str
    region_code: str | None
    stage: str
    stage_label: str
    status: str
    payment_status: str
    version: int
    submitted_at: datetime | None
    decided_at: datetime | None
    decision: str | None
    created_at: datetime
    updated_at: datetime

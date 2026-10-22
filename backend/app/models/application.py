import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, Integer, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import GUID, JSONType


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    year_label: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    public_notice_start: Mapped[date | None] = mapped_column(Date)
    public_notice_end: Mapped[date | None] = mapped_column(Date)


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    route_type: Mapped[str] = mapped_column(String(50), nullable=False)
    stages: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    transitions: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ApplicationCategory(Base):
    __tablename__ = "application_categories"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    processing_category: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    requires_self_disclosure: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_scrutiny: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_evc: Mapped[bool] = mapped_column(Boolean, default=False)
    sac_shc_applicable: Mapped[str] = mapped_column(String(10), default="AA")
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("workflow_definitions.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    reference_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    institution_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("institutions.id"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("application_categories.id"), nullable=False)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("academic_years.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    assigned_officer_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    region_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("regions.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    form_data: Mapped[dict | None] = mapped_column(JSONType())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision: Mapped[str | None] = mapped_column(String(50))
    decision_remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    institution = relationship("Institution", lazy="selectin")
    category = relationship("ApplicationCategory", lazy="selectin")
    academic_year = relationship("AcademicYear", lazy="selectin")


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), unique=True, nullable=False)
    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workflow_definitions.id"), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StageEntry(Base):
    __tablename__ = "stage_entries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entered_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    remarks: Mapped[str | None] = mapped_column(Text)


class TransitionEvent(Base):
    __tablename__ = "transition_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    rule_family_code: Mapped[str | None] = mapped_column(String(100))
    rule_version: Mapped[int | None] = mapped_column(Integer)
    remarks: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ClockEvent(Base):
    __tablename__ = "clock_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    clock_owner: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    authorised_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    extended_deadline: Mapped[date | None] = mapped_column(Date)
    previous_deadline: Mapped[date | None] = mapped_column(Date)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False)
    assignee_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DeficiencyRecord(Base):
    __tablename__ = "deficiency_records"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False)
    raised_by: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="MAJOR")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    response: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

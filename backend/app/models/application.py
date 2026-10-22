import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, Integer, Boolean, Date, DateTime, Text, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import GUID, JSONType, UTCDateTime


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
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))


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
    __table_args__ = (
        Index("ix_applications_stage_status", "stage", "status"),
        Index("ix_applications_region_id", "region_id"),
        Index("ix_applications_institution_id", "institution_id"),
        Index("ix_applications_academic_year_id", "academic_year_id"),
        Index("ix_applications_assigned_officer_id", "assigned_officer_id"),
    )

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
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    decision: Mapped[str | None] = mapped_column(String(50))
    decision_remarks: Mapped[str | None] = mapped_column(Text)
    # Payment is MOCK until a real gateway is authorised (spec §11.5). A MOCK
    # confirmation is never a real transaction and is labelled as such everywhere.
    payment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="NOT_INITIATED", server_default="NOT_INITIATED"
    )
    payment_reference: Mapped[str | None] = mapped_column(String(100))
    payment_confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    form_schema_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
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
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class StageEntry(Base):
    __tablename__ = "stage_entries"
    __table_args__ = (
        Index("ix_stage_entries_application_id", "application_id"),
        # At most one open stage per application: concurrent transitions cannot
        # leave two "current" stages in the history.
        Index(
            "uq_stage_entries_one_open", "application_id", unique=True,
            sqlite_where=text("exited_at IS NULL"), postgresql_where=text("exited_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    exited_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    entered_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    remarks: Mapped[str | None] = mapped_column(Text)


class TransitionEvent(Base):
    __tablename__ = "transition_events"
    __table_args__ = (
        # sequence_no = application.version the transition moved FROM. The unique
        # constraint makes it impossible for two concurrent requests that read the
        # same version to both commit (database-level optimistic lock).
        UniqueConstraint("application_id", "sequence_no", name="uq_transition_events_app_seq"),
        Index("ix_transition_events_app_time", "application_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False)
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    rule_family_code: Mapped[str | None] = mapped_column(String(100))
    rule_version: Mapped[int | None] = mapped_column(Integer)
    remarks: Mapped[str | None] = mapped_column(Text)
    sequence_no: Mapped[int | None] = mapped_column(Integer)
    actor_role: Mapped[str | None] = mapped_column(String(100))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONType())
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))


class ClockEvent(Base):
    __tablename__ = "clock_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    clock_owner: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
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
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))


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
    responded_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))

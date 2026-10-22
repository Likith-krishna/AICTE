import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, Boolean, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID, JSONType


class EVCQueueEntry(Base):
    __tablename__ = "evc_queue_entries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("applications.id"), nullable=False)
    region_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("regions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="ONLINE")
    scheduled_date: Mapped[date | None] = mapped_column(Date)
    completed_date: Mapped[date | None] = mapped_column(Date)
    coordinator_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    report_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    report_data: Mapped[dict | None] = mapped_column(JSONType())
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class EVCMemberAssignment(Base):
    __tablename__ = "evc_member_assignments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    evc_entry_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("evc_queue_entries.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    role_in_evc: Mapped[str] = mapped_column(String(50), nullable=False, default="MEMBER")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

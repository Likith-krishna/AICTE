import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, Integer, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID, JSONType


class APHSourceDocument(Base):
    __tablename__ = "aph_source_documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    edition: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1000))
    total_pages: Mapped[int | None] = mapped_column(Integer)
    registered_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REGISTERED")
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("aph_source_documents.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class APHSourceProvision(Base):
    __tablename__ = "aph_source_provisions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("aph_source_documents.id"), nullable=False)
    chapter: Mapped[str | None] = mapped_column(String(20))
    section: Mapped[str | None] = mapped_column(String(50))
    clause: Mapped[str | None] = mapped_column(String(50))
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    provision_text: Mapped[str] = mapped_column(Text, nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="CANDIDATE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RegulatoryRule(Base):
    __tablename__ = "regulatory_rules"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    rule_family_code: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    aph_document_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("aph_source_documents.id"))
    aph_clause: Mapped[str | None] = mapped_column(String(100))
    aph_page: Mapped[str | None] = mapped_column(String(50))
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNVERIFIED")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    rule_logic: Mapped[dict | None] = mapped_column(JSONType())
    parameters: Mapped[dict | None] = mapped_column(JSONType())
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class RuleReviewHistory(Base):
    __tablename__ = "rule_review_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("regulatory_rules.id"), nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

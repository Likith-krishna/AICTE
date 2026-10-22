import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import GUID, UTCDateTime


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))

    institutions = relationship("Institution", back_populates="region", lazy="selectin")


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pid: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    institution_type: Mapped[str] = mapped_column(String(100), nullable=False, default="private")
    region_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("regions.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(1000))
    pincode: Mapped[str | None] = mapped_column(String(10))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    established_year: Mapped[int | None] = mapped_column()
    website: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    region = relationship("Region", back_populates="institutions", lazy="selectin")
    users = relationship("User", back_populates="institution", lazy="selectin")

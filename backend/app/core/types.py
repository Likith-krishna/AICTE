"""Database type compatibility for PostgreSQL and SQLite."""
import uuid
import json

from datetime import timezone

from sqlalchemy import DateTime, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB


class GUID(TypeDecorator):
    """Platform-independent UUID type. Uses PG UUID on PostgreSQL, CHAR(36) elsewhere."""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class JSONType(TypeDecorator):
    """Platform-independent JSON type. Uses JSONB on PostgreSQL, TEXT+JSON elsewhere."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetime on every backend.

    PostgreSQL stores TIMESTAMPTZ natively. SQLite has no timezone support and
    returns naive values; all values are written in UTC, so naive results are
    re-tagged as UTC. This keeps API timestamps unambiguous (ISO-8601 with +00:00).
    """
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
            if dialect.name != "postgresql":
                value = value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

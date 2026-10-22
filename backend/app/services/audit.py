import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system import AuditEvent


async def log_audit_event(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
):
    event = AuditEvent(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
        ip_address=ip_address,
    )
    db.add(event)
    await db.flush()
    return event

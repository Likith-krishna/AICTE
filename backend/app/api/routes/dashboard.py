from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.scoping import application_scope, apply_scope
from app.core import roles as R
from app.models.user import User
from app.models.application import Application
from app.models.institution import Institution
from app.models.compliance import ComplianceObligation
from app.models.notification import NotificationDelivery

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope = application_scope(current_user, aggregate_only=True)

    def scoped_apps(q):
        q = apply_scope(q, scope, institution_col=Application.institution_id, region_col=Application.region_id)
        # Drafts are private to the institution until submitted.
        if current_user.role not in R.INSTITUTION_ROLES:
            q = q.where(Application.stage != "DRAFT")
        return q

    total_apps = (await db.execute(scoped_apps(select(func.count(Application.id))))).scalar() or 0

    stage_result = await db.execute(
        scoped_apps(select(Application.stage, func.count(Application.id))).group_by(Application.stage)
    )
    stage_counts = {row[0]: row[1] for row in stage_result.all()}

    compliance_q = (
        select(func.count(ComplianceObligation.id))
        .join(Institution, Institution.id == ComplianceObligation.institution_id)
        .where(ComplianceObligation.status == "PENDING")
    )
    compliance_q = apply_scope(
        compliance_q, scope,
        institution_col=ComplianceObligation.institution_id, region_col=Institution.region_id,
    )
    pending_compliance = (await db.execute(compliance_q)).scalar() or 0

    unread_notifications = (await db.execute(
        select(func.count(NotificationDelivery.id))
        .where(NotificationDelivery.recipient_user_id == current_user.id)
        .where(NotificationDelivery.read_at.is_(None))
    )).scalar() or 0

    return {
        "total_applications": total_apps,
        "applications_by_stage": stage_counts,
        "pending_compliance": pending_compliance,
        "unread_notifications": unread_notifications,
    }

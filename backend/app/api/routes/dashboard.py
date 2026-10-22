from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.application import Application
from app.models.compliance import ComplianceObligation
from app.models.notification import NotificationDelivery

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app_count_q = select(func.count(Application.id))
    if current_user.role == "institution_applicant" and current_user.institution_id:
        app_count_q = app_count_q.where(Application.institution_id == current_user.institution_id)
    elif current_user.role in ("regional_officer", "scrutiny_officer") and current_user.region_id:
        app_count_q = app_count_q.where(Application.region_id == current_user.region_id)

    total_apps = (await db.execute(app_count_q)).scalar() or 0

    stage_counts_q = select(Application.stage, func.count(Application.id)).group_by(Application.stage)
    if current_user.role == "institution_applicant" and current_user.institution_id:
        stage_counts_q = stage_counts_q.where(Application.institution_id == current_user.institution_id)
    elif current_user.role in ("regional_officer", "scrutiny_officer") and current_user.region_id:
        stage_counts_q = stage_counts_q.where(Application.region_id == current_user.region_id)

    stage_result = await db.execute(stage_counts_q)
    stage_counts = {row[0]: row[1] for row in stage_result.all()}

    pending_compliance = (await db.execute(
        select(func.count(ComplianceObligation.id)).where(ComplianceObligation.status == "PENDING")
    )).scalar() or 0

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

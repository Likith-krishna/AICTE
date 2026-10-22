"""Application lifecycle API (Phase 3).

All access is scoped server-side via app.core.scoping; client-supplied
institution/region identifiers are never trusted for authorisation.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, or_, select, update as sa_update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import roles as R
from app.core.database import get_db
from app.core.scoping import application_scope, apply_scope, scope_allows
from app.core.security import get_current_user, require_roles
from app.models.application import (
    AcademicYear, Application, ApplicationCategory, ClockEvent, StageEntry,
    TransitionEvent, WorkflowDefinition, WorkflowInstance,
)
from app.models.institution import Institution, Region
from app.models.user import User
from app.schemas.application import (
    AcademicYearOption, ApplicationCreateRequest, ApplicationListItem, ApplicationUpdateRequest,
    CategoryResponse, TransitionRequest, VersionedRequest,
)
from app.schemas.common import PaginatedResponse
from app.services import workflow as wf
from app.services.audit import log_audit_event
from app.services.form_schemas import FORM_SCHEMA_VERSION, get_form_schema, validate_form_data

router = APIRouter(prefix="/api/applications", tags=["applications"])

SORT_COLUMNS = {
    "created_at": Application.created_at,
    "updated_at": Application.updated_at,
    "submitted_at": Application.submitted_at,
    "reference_number": Application.reference_number,
    "stage": Application.stage,
}


def _error(exc: wf.WorkflowError) -> HTTPException:
    return HTTPException(status_code=exc.status_code,
                         detail={"message": exc.message, "code": exc.code, **exc.details})


async def _definitions(db: AsyncSession) -> dict[UUID, wf.Definition]:
    rows = (await db.execute(select(WorkflowDefinition))).scalars().all()
    return {r.id: wf.load_definition(r) for r in rows}


async def _load_scoped(db: AsyncSession, application_id: UUID, user: User) -> Application:
    scope = application_scope(user)
    app_obj = (await db.execute(
        select(Application).where(Application.id == application_id).execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if app_obj is None:
        # Scoped users get 403 for unknown IDs as well, so IDs cannot be probed.
        if scope.kind != "national":
            raise HTTPException(status_code=403, detail="You do not have access to this application")
        raise HTTPException(status_code=404, detail="Application not found")
    if not scope_allows(scope, institution_id=app_obj.institution_id, region_id=app_obj.region_id):
        raise HTTPException(status_code=403, detail="You do not have access to this application")
    if app_obj.stage == "DRAFT" and user.role not in R.INSTITUTION_ROLES:
        raise HTTPException(status_code=403, detail="Draft applications are private to the institution")
    return app_obj


def _actionable_pairs(defs: dict[UUID, wf.Definition], role: str) -> list[tuple[UUID, set[str]]]:
    pairs = []
    for wf_id, d in defs.items():
        stages = {t.from_stage for t in d.transitions if wf.requires_human(d, t) and role in wf.effective_roles(d, t)}
        if stages:
            pairs.append((wf_id, stages))
    return pairs


# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(ApplicationCategory, WorkflowDefinition)
        .join(WorkflowDefinition, WorkflowDefinition.id == ApplicationCategory.workflow_definition_id)
        .where(ApplicationCategory.is_active.is_(True))
        .order_by(ApplicationCategory.processing_category, ApplicationCategory.name)
    )).all()
    return [
        CategoryResponse(
            id=c.id, code=c.code, name=c.name, processing_category=c.processing_category,
            requires_self_disclosure=c.requires_self_disclosure, requires_scrutiny=c.requires_scrutiny,
            requires_evc=c.requires_evc, sac_shc_applicable=c.sac_shc_applicable,
            route_type=w.route_type, workflow_name=w.name,
        )
        for c, w in rows
    ]


@router.get("/academic-years", response_model=list[AcademicYearOption])
async def list_academic_years(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(AcademicYear).order_by(AcademicYear.start_date.desc()))).scalars().all()
    return [AcademicYearOption.model_validate(r) for r in rows]


@router.get("/form-schema/{category_code}")
async def form_schema(
    category_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exists = (await db.execute(
        select(ApplicationCategory.id).where(ApplicationCategory.code == category_code)
    )).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Unknown application category")
    return get_form_schema(category_code)


# --------------------------------------------------------------------------- #
# List / create
# --------------------------------------------------------------------------- #

@router.get("", response_model=PaginatedResponse)
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    stage: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    category_id: UUID | None = None,
    academic_year_id: UUID | None = None,
    region_id: UUID | None = None,
    needs_my_action: bool = False,
    sort_by: str = Query("updated_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    scope = application_scope(current_user)
    if scope.is_none and current_user.role not in (R.INSTITUTION_ROLES | R.REGIONAL_ROLES):
        raise HTTPException(status_code=403, detail="Your role does not have access to application records")
    # Institution/regional users without an assignment fall through to an empty result.
    defs = await _definitions(db)

    base = (
        select(Application, Institution, ApplicationCategory, AcademicYear, Region, WorkflowInstance)
        .join(Institution, Institution.id == Application.institution_id)
        .join(ApplicationCategory, ApplicationCategory.id == Application.category_id)
        .join(AcademicYear, AcademicYear.id == Application.academic_year_id)
        .outerjoin(Region, Region.id == Application.region_id)
        .outerjoin(WorkflowInstance, WorkflowInstance.application_id == Application.id)
    )
    base = apply_scope(base, scope, institution_col=Application.institution_id, region_col=Application.region_id)
    if current_user.role not in R.INSTITUTION_ROLES:
        base = base.where(Application.stage != "DRAFT")
    if search:
        pat = f"%{search.strip()}%"
        base = base.where(or_(Application.reference_number.ilike(pat), Institution.name.ilike(pat)))
    if stage:
        base = base.where(Application.stage == stage)
    if status_filter:
        base = base.where(Application.status == status_filter)
    if category_id:
        base = base.where(Application.category_id == category_id)
    if academic_year_id:
        base = base.where(Application.academic_year_id == academic_year_id)
    if region_id:
        base = base.where(Application.region_id == region_id)

    pairs = _actionable_pairs(defs, current_user.role)
    if needs_my_action:
        if not pairs:
            base = base.where(Application.id.is_(None))
        else:
            base = base.where(Application.status == "ACTIVE").where(or_(*[
                and_(WorkflowInstance.workflow_definition_id == wid, Application.stage.in_(stages))
                for wid, stages in pairs
            ]))

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    col = SORT_COLUMNS.get(sort_by, Application.updated_at)
    order = col.desc() if sort_dir == "desc" else col.asc()
    rows = (await db.execute(
        base.order_by(order, Application.id).offset((page - 1) * page_size).limit(page_size)
    )).all()

    actionable = {wid: stages for wid, stages in pairs}
    items = []
    for a, inst, cat, ay, reg, wi in rows:
        d = defs.get(wi.workflow_definition_id if wi else cat.workflow_definition_id)
        item = ApplicationListItem(
            id=a.id, reference_number=a.reference_number, institution_id=a.institution_id,
            institution_name=inst.name, category_code=cat.code, category_name=cat.name,
            route_type=d.model.route_type if d else "", academic_year=ay.year_label,
            region_code=reg.code if reg else None, stage=a.stage,
            stage_label=d.stage_label(a.stage) if d else a.stage, status=a.status,
            payment_status=a.payment_status, version=a.version, submitted_at=a.submitted_at,
            decided_at=a.decided_at, decision=a.decision, created_at=a.created_at, updated_at=a.updated_at,
        ).model_dump(mode="json")
        item["needs_my_action"] = bool(
            a.status == "ACTIVE" and wi and a.stage in actionable.get(wi.workflow_definition_id, set())
        )
        items.append(item)

    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


async def _next_reference(db: AsyncSession, ay: AcademicYear, region: Region) -> str:
    prefix = f"FG/{ay.year_label}/{region.code}/"
    count = (await db.execute(
        select(func.count()).select_from(Application).where(Application.reference_number.like(f"{prefix}%"))
    )).scalar() or 0
    return f"{prefix}{count + 1:05d}"


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_application(
    request: ApplicationCreateRequest,
    current_user: User = Depends(require_roles(R.INSTITUTION_APPLICANT)),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.institution_id:
        raise HTTPException(status_code=403, detail="Your account is not linked to an institution")
    institution = (await db.execute(
        select(Institution).where(Institution.id == current_user.institution_id)
    )).scalar_one_or_none()
    if institution is None:
        raise HTTPException(status_code=403, detail="Your account is not linked to a valid institution")
    category = (await db.execute(
        select(ApplicationCategory).where(ApplicationCategory.id == request.category_id)
    )).scalar_one_or_none()
    if category is None or not category.is_active:
        raise HTTPException(status_code=422, detail="Unknown or inactive application category")
    ay = (await db.execute(select(AcademicYear).where(AcademicYear.id == request.academic_year_id))).scalar_one_or_none()
    if ay is None:
        raise HTTPException(status_code=422, detail="Unknown academic year")
    wf_def = (await db.execute(
        select(WorkflowDefinition).where(WorkflowDefinition.id == category.workflow_definition_id)
    )).scalar_one()
    if not wf_def.is_active:
        raise HTTPException(status_code=422, detail="The workflow for this category is not active")

    clean, errors = validate_form_data(category.code, request.form_data, partial=True)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Form data is invalid", "code": "FORM_INVALID",
                                                     "field_errors": errors})
    region = (await db.execute(select(Region).where(Region.id == institution.region_id))).scalar_one()

    application = None
    for _attempt in range(5):
        ref = await _next_reference(db, ay, region)
        try:
            async with db.begin_nested():
                application = Application(
                    reference_number=ref, institution_id=institution.id, category_id=category.id,
                    academic_year_id=ay.id, region_id=institution.region_id, stage="DRAFT", status="ACTIVE",
                    version=1, form_data=clean, form_schema_version=FORM_SCHEMA_VERSION,
                )
                db.add(application)
                await db.flush()
            break
        except IntegrityError:
            application = None
            continue
    if application is None:
        raise HTTPException(status_code=409, detail="Could not allocate a reference number; please retry")

    await wf.ensure_instance(db, application, wf_def.id, created_by=current_user.id)
    await log_audit_event(
        db, actor_id=current_user.id, actor_role=current_user.role, action="APPLICATION_CREATED",
        entity_type="Application", entity_id=application.id,
        changes={"reference_number": application.reference_number, "category": category.code,
                 "academic_year": ay.year_label, "workflow_definition": f"{wf_def.name} v{wf_def.version}"},
    )
    await db.commit()
    return await _detail(db, application.id, current_user)


# --------------------------------------------------------------------------- #
# Detail / update / withdraw
# --------------------------------------------------------------------------- #

async def _detail(db: AsyncSession, application_id: UUID, user: User) -> dict[str, Any]:
    a = await _load_scoped(db, application_id, user)
    inst = (await db.execute(select(Institution).where(Institution.id == a.institution_id))).scalar_one()
    cat = (await db.execute(select(ApplicationCategory).where(ApplicationCategory.id == a.category_id))).scalar_one()
    ay = (await db.execute(select(AcademicYear).where(AcademicYear.id == a.academic_year_id))).scalar_one()
    reg = (await db.execute(select(Region).where(Region.id == a.region_id))).scalar_one_or_none()
    defn, wi = await wf.get_definition_for(db, a)
    clock_events = (await db.execute(
        select(ClockEvent).where(ClockEvent.application_id == a.id).order_by(ClockEvent.occurred_at)
    )).scalars().all()

    is_owner_institution = user.role in R.INSTITUTION_ROLES and user.institution_id == a.institution_id
    can_edit = (
        a.stage == "DRAFT" and a.status == "ACTIVE" and is_owner_institution and user.role == R.INSTITUTION_APPLICANT
    )
    form_errors: dict[str, str] = {}
    if a.stage == "DRAFT":
        _, form_errors = validate_form_data(cat.code, a.form_data, partial=False)

    can_mock_pay = (
        a.status == "ACTIVE" and a.stage == "SUBMITTED" and is_owner_institution
        and user.role == R.INSTITUTION_APPLICANT and a.payment_status not in wf.PAYMENT_CONFIRMED_STATES
    )
    return {
        "id": str(a.id),
        "reference_number": a.reference_number,
        "institution": {"id": str(inst.id), "name": inst.name, "pid": inst.pid, "city": inst.city, "state": inst.state},
        "category": {"id": str(cat.id), "code": cat.code, "name": cat.name, "processing_category": cat.processing_category,
                     "requires_scrutiny": cat.requires_scrutiny, "requires_evc": cat.requires_evc,
                     "requires_self_disclosure": cat.requires_self_disclosure,
                     "sac_shc_applicable": cat.sac_shc_applicable},
        "academic_year": {"id": str(ay.id), "year_label": ay.year_label},
        "region": {"id": str(reg.id), "code": reg.code, "name": reg.name} if reg else None,
        "workflow": {"id": str(defn.model.id), "name": defn.model.name, "version": defn.model.version,
                     "route_type": defn.model.route_type,
                     "stages": [{"code": k, "label": v.get("label", k), "type": v.get("type")} for k, v in defn.stages.items()]},
        "stage": a.stage,
        "stage_label": defn.stage_label(a.stage),
        "stage_type": defn.stage_type(a.stage),
        "stage_note": wf.STAGE_NOTES.get(a.stage),
        "status": a.status,
        "version": a.version,
        "form_data": a.form_data or {},
        "form_schema_version": a.form_schema_version,
        "form_errors": form_errors,
        "payment": {
            "status": a.payment_status, "reference": a.payment_reference,
            "confirmed_at": a.payment_confirmed_at.isoformat() if a.payment_confirmed_at else None,
            "is_mock": a.payment_status == wf.PAYMENT_MOCK_CONFIRMED,
            "fee_note": "Fee amount is not computed: TER fee rules are not yet published in the rule registry.",
        },
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
        "decision": a.decision,
        "decision_remarks": a.decision_remarks,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
        "permissions": {"can_edit": can_edit, "can_withdraw": can_edit, "can_mock_pay": can_mock_pay},
        "available_actions": wf.available_actions(defn, a, user, cat.code),
        "clock": wf.summarise_clock(list(clock_events)),
    }


@router.get("/{application_id}")
async def get_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _detail(db, application_id, current_user)


@router.patch("/{application_id}")
async def update_draft(
    application_id: UUID,
    request: ApplicationUpdateRequest,
    current_user: User = Depends(require_roles(R.INSTITUTION_APPLICANT)),
    db: AsyncSession = Depends(get_db),
):
    a = await _load_scoped(db, application_id, current_user)
    if a.stage != "DRAFT" or a.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Only active draft applications can be edited")
    if a.version != request.expected_version:
        raise HTTPException(status_code=409, detail={"message": "The draft was changed since you loaded it. Reload and try again.",
                                                     "code": "STALE_VERSION", "current_version": a.version})
    cat = (await db.execute(select(ApplicationCategory).where(ApplicationCategory.id == a.category_id))).scalar_one()
    clean, errors = validate_form_data(cat.code, request.form_data, partial=True)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Form data is invalid", "code": "FORM_INVALID",
                                                     "field_errors": errors})
    old = a.form_data or {}
    changed = sorted(k for k in set(old) | set(clean) if old.get(k) != clean.get(k))
    res = await db.execute(
        sa_update(Application).where(Application.id == a.id).where(Application.version == a.version)
        .values(form_data=clean, version=a.version + 1, updated_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    if res.rowcount != 1:
        raise HTTPException(status_code=409, detail={"message": "Concurrent modification. Reload and try again.",
                                                     "code": "CONCURRENT_MODIFICATION"})
    await db.execute(
        sa_update(WorkflowInstance).where(WorkflowInstance.application_id == a.id).values(version=a.version + 1)
    )
    await log_audit_event(
        db, actor_id=current_user.id, actor_role=current_user.role, action="APPLICATION_DRAFT_UPDATED",
        entity_type="Application", entity_id=a.id, changes={"fields_changed": changed},
    )
    await db.commit()
    return await _detail(db, application_id, current_user)


@router.post("/{application_id}/withdraw")
async def withdraw_draft(
    application_id: UUID,
    request: VersionedRequest,
    current_user: User = Depends(require_roles(R.INSTITUTION_APPLICANT)),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw an unsubmitted draft. Records are retained (never deleted) for audit."""
    a = await _load_scoped(db, application_id, current_user)
    if a.stage != "DRAFT" or a.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Only active draft applications can be withdrawn")
    res = await db.execute(
        sa_update(Application).where(Application.id == a.id).where(Application.version == request.expected_version)
        .values(status="WITHDRAWN", version=a.version + 1, updated_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    if res.rowcount != 1:
        raise HTTPException(status_code=409, detail={"message": "The draft was changed since you loaded it.",
                                                     "code": "STALE_VERSION"})
    await log_audit_event(
        db, actor_id=current_user.id, actor_role=current_user.role, action="APPLICATION_WITHDRAWN",
        entity_type="Application", entity_id=a.id, changes={"remarks": request.remarks},
    )
    await db.commit()
    return await _detail(db, application_id, current_user)


# --------------------------------------------------------------------------- #
# Workflow
# --------------------------------------------------------------------------- #

async def _commit_or_conflict(db: AsyncSession):
    try:
        await db.commit()
    except (IntegrityError, OperationalError) as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail={
            "message": "Another action on this application completed first. Reload and try again.",
            "code": "CONCURRENT_MODIFICATION"}) from exc


@router.post("/{application_id}/transition")
async def transition(
    application_id: UUID,
    request: TransitionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    a = await _load_scoped(db, application_id, current_user)
    cat = (await db.execute(select(ApplicationCategory).where(ApplicationCategory.id == a.category_id))).scalar_one()
    try:
        events = await wf.perform_transition(
            db, application=a, category_code=cat.code, actor=current_user, to_stage=request.to_stage,
            remarks=request.remarks, expected_version=request.expected_version,
        )
    except wf.WorkflowError as exc:
        await db.rollback()
        raise _error(exc)
    except (IntegrityError, OperationalError) as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail={
            "message": "Another action on this application completed first. Reload and try again.",
            "code": "CONCURRENT_MODIFICATION"}) from exc
    await _commit_or_conflict(db)
    detail = await _detail(db, application_id, current_user)
    detail["applied_transitions"] = [
        {"from_stage": e.from_stage, "to_stage": e.to_stage, "trigger_type": e.trigger_type} for e in events
    ]
    return detail


@router.post("/{application_id}/mock-payment")
async def mock_payment(
    application_id: UUID,
    request: VersionedRequest,
    current_user: User = Depends(require_roles(R.INSTITUTION_APPLICANT)),
    db: AsyncSession = Depends(get_db),
):
    """Simulated payment confirmation (spec §11.5: payment gateway is MOCK).

    This is NOT a real payment. It records a MOCK reference so the workflow's
    automatic SUBMITTED → PAYMENT_VERIFIED step can be demonstrated.
    """
    a = await _load_scoped(db, application_id, current_user)
    if a.stage != "SUBMITTED" or a.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Mock payment is only possible for a submitted application awaiting payment")
    if a.payment_status in wf.PAYMENT_CONFIRMED_STATES:
        raise HTTPException(status_code=409, detail={"message": "Payment already recorded", "code": "ALREADY_PAID"})
    if a.version != request.expected_version:
        raise HTTPException(status_code=409, detail={"message": "The application was changed since you loaded it.",
                                                     "code": "STALE_VERSION"})
    now = datetime.now(timezone.utc)
    ref = f"MOCK-{now:%Y%m%d}-{secrets.token_hex(4).upper()}"
    res = await db.execute(
        sa_update(Application).where(Application.id == a.id).where(Application.version == a.version)
        .where(Application.payment_status == wf.PAYMENT_NOT_INITIATED)
        .values(payment_status=wf.PAYMENT_MOCK_CONFIRMED, payment_reference=ref, payment_confirmed_at=now)
        .execution_options(synchronize_session=False)
    )
    if res.rowcount != 1:
        raise HTTPException(status_code=409, detail={"message": "Payment state changed concurrently.",
                                                     "code": "CONCURRENT_MODIFICATION"})
    await log_audit_event(
        db, actor_id=current_user.id, actor_role=current_user.role, action="MOCK_PAYMENT_CONFIRMED",
        entity_type="Application", entity_id=a.id,
        changes={"is_mock": True, "payment_reference": ref,
                 "note": "Simulated confirmation — not a real transaction; fee amount not computed"},
    )
    await db.flush()
    a = (await db.execute(
        select(Application).where(Application.id == application_id).execution_options(populate_existing=True)
    )).scalar_one()
    defn, wi = await wf.get_definition_for(db, a)
    cat = (await db.execute(select(ApplicationCategory).where(ApplicationCategory.id == a.category_id))).scalar_one()
    try:
        await wf.run_automatic_transitions(db, defn=defn, instance=wi, application=a, category_code=cat.code)
    except wf.WorkflowError as exc:
        await db.rollback()
        raise _error(exc)
    await _commit_or_conflict(db)
    return await _detail(db, application_id, current_user)


@router.get("/{application_id}/timeline")
async def timeline(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    a = await _load_scoped(db, application_id, current_user)
    transitions = (await db.execute(
        select(TransitionEvent).where(TransitionEvent.application_id == a.id)
        .order_by(TransitionEvent.occurred_at, TransitionEvent.sequence_no)
    )).scalars().all()
    stages = (await db.execute(
        select(StageEntry).where(StageEntry.application_id == a.id).order_by(StageEntry.entered_at)
    )).scalars().all()
    clocks = (await db.execute(
        select(ClockEvent).where(ClockEvent.application_id == a.id).order_by(ClockEvent.occurred_at)
    )).scalars().all()
    defn, _ = await wf.get_definition_for(db, a)

    actor_ids = {t.triggered_by for t in transitions if t.triggered_by} | {s.entered_by for s in stages if s.entered_by}
    actors = {}
    if actor_ids:
        for u in (await db.execute(select(User).where(User.id.in_(actor_ids)))).scalars().all():
            actors[u.id] = u
    viewer_is_institution = current_user.role in R.INSTITUTION_ROLES

    def actor_view(uid):
        if uid is None:
            return {"name": "System", "role": "system"}
        u = actors.get(uid)
        if u is None:
            return {"name": None, "role": None}
        # Institution users see officials by role only, not by name.
        if viewer_is_institution and u.institution_id != current_user.institution_id:
            return {"name": None, "role": u.role}
        return {"name": u.full_name, "role": u.role}

    def iso(d):
        return d.isoformat() if d else None

    return {
        "application_id": str(a.id),
        "transitions": [{
            "id": str(t.id), "sequence_no": t.sequence_no, "from_stage": t.from_stage,
            "from_stage_label": defn.stage_label(t.from_stage), "to_stage": t.to_stage,
            "to_stage_label": defn.stage_label(t.to_stage), "trigger_type": t.trigger_type,
            "actor": actor_view(t.triggered_by), "remarks": t.remarks,
            "rule_family_code": t.rule_family_code, "rule_version": t.rule_version,
            "metadata": t.metadata_ or {}, "occurred_at": iso(t.occurred_at),
        } for t in transitions],
        "stage_entries": [{
            "id": str(s.id), "stage": s.stage, "stage_label": defn.stage_label(s.stage),
            "entered_at": iso(s.entered_at), "exited_at": iso(s.exited_at),
            "duration_seconds": round(((s.exited_at or datetime.now(timezone.utc)) - s.entered_at).total_seconds())
            if s.entered_at else None,
            "entered_by": actor_view(s.entered_by), "remarks": s.remarks,
        } for s in stages],
        "clock_events": [{
            "id": str(c.id), "event_type": c.event_type, "clock_owner": c.clock_owner,
            "occurred_at": iso(c.occurred_at), "reason": c.reason,
        } for c in clocks],
        "clock": wf.summarise_clock(list(clocks)),
    }

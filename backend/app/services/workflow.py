"""Deterministic workflow engine for application stage transitions.

The engine executes the *versioned workflow definitions* stored in
``workflow_definitions`` (seeded from spec §4.2). It adds only the safeguards
the specification requires; it does not invent regulatory rules:

* Role guard ........ the definition's ``role`` (plus documented equivalents).
* Scope guard ....... institution / region scoping (app/core/scoping.py).
* Human authority ... spec §4.3 "System never automatically approves or rejects":
                      any transition INTO a decision/final/terminal stage needs a
                      named human actor, even if the definition marks it AUTOMATIC.
* Preconditions ..... data-completeness checks (form complete, MOCK payment
                      recorded, remarks for decisions). These are workflow
                      hygiene, not APH rules, and are labelled as such.
* Concurrency ....... optimistic version check + UNIQUE(application_id, sequence_no)
                      + one-open-stage partial unique index.
* History ........... TransitionEvent, StageEntry, ClockEvent and AuditEvent are
                      written in the same transaction as the stage change.

Clock ownership per stage is a PROTOTYPE POLICY (spec §5.1 describes the
concept but no per-stage mapping or durations are APH-mandated); it records
elapsed time only and never computes deadlines.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core import roles as R
from app.core.scoping import application_scope, scope_allows
from app.models.application import (
    Application, ApplicationCategory, ClockEvent, StageEntry, TransitionEvent,
    WorkflowDefinition, WorkflowInstance,
)
from app.models.rules import RegulatoryRule
from app.services.audit import log_audit_event
from app.services.form_schemas import validate_form_data

# --------------------------------------------------------------------------- #
# Static engine configuration
# --------------------------------------------------------------------------- #

# Spec §2.1 groups "Regional Officer / Scrutiny Officer" in one row with the
# same permitted actions, so scrutiny transitions accept either role.
ROLE_EQUIVALENTS: dict[str, frozenset[str]] = {
    R.SCRUTINY_OFFICER: frozenset({R.SCRUTINY_OFFICER, R.REGIONAL_OFFICER}),
}

HUMAN_DECISION_STAGE_TYPES = frozenset({"decision", "final", "terminal"})

# Transitions that require written remarks (reasons must be recorded for
# deficiencies, recommendations, decisions and appeals).
REMARKS_REQUIRED_TARGETS = frozenset({
    "DEFICIENCY_NOTED", "DEFICIENCY_DETECTED", "RESPONSE_RECEIVED",
    "SHC_RECOMMENDATION", "SAC_HEARING", "SAC_RECOMMENDATION",
    "APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "FINAL_REJECTION", "EOA_ISSUED",
})
MIN_REMARKS_LENGTH = 10

DECISION_OUTCOME_STAGES = frozenset({
    "APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "FINAL_REJECTION", "EOA_ISSUED",
})

# Prototype clock policy: stages where the institution must act.
INSTITUTION_CLOCK_STAGES = frozenset({"SUBMITTED", "AWAITING_INSTITUTION_RESPONSE", "REJECTED"})
CLOCK_POLICY_NOTE = "Prototype stage→clock-owner mapping (spec §5.1 concept); not APH-mandated; no deadlines computed."

ACTION_LABELS: dict[str, str] = {
    "SUBMITTED": "Submit application",
    "SCRUTINY_CLEAR": "Mark scrutiny clear",
    "DEFICIENCY_NOTED": "Record deficiency",
    "RESPONSE_RECEIVED": "Submit deficiency response",
    "EVC_SCHEDULED": "Schedule EVC",
    "EVC_IN_PROGRESS": "Start EVC",
    "EVC_COMPLETED": "Mark EVC completed",
    "REPORT_SUBMITTED": "Submit EVC report",
    "SHC_COMPLIANCE": "Refer to Standing Hearing Committee",
    "SHC_RECOMMENDATION": "Record SHC recommendation",
    "PLACED_BEFORE_EC": "Place before Executive Committee",
    "EC_DECISION": "Take up for EC decision",
    "APPROVED": "Approve",
    "APPROVED_WITH_CONDITIONS": "Approve with conditions",
    "REJECTED": "Reject",
    "SAC_HEARING": "File appeal to SAC",
    "SAC_RECOMMENDATION": "Record SAC recommendation",
    "FINAL_REJECTION": "Confirm final rejection",
    "DEFICIENCY_FREE": "Mark deficiency-free",
    "DEFICIENCY_DETECTED": "Record deficiency",
    "EOA_ISSUED": "Issue Extension of Approval",
}

ACTION_TONE: dict[str, str] = {
    "APPROVED": "approve", "APPROVED_WITH_CONDITIONS": "approve", "EOA_ISSUED": "approve",
    "SCRUTINY_CLEAR": "approve", "DEFICIENCY_FREE": "approve",
    "REJECTED": "reject", "FINAL_REJECTION": "reject",
    "DEFICIENCY_NOTED": "warn", "DEFICIENCY_DETECTED": "warn",
}

# Notes surfaced to users on specific transitions/stages, citing spec items.
TRANSITION_NOTES: dict[tuple[str, str], str] = {
    ("REPORT_SUBMITTED", "SHC_COMPLIANCE"): (
        "SHC/SAC applicability is 'As Applicable' (APH Table 2.3). The criteria are pending "
        "authorised clarification (spec §13.2 A1/A2); the referral is the Bureau Officer's judgement."
    ),
    ("REJECTED", "SAC_HEARING"): (
        "APH Cl. 1.11(a) / 2.24(a) allow one appeal within 7 days. The deadline rule is not yet "
        "published in the rule registry, so the system does NOT enforce it — verify the window manually."
    ),
    ("DEFICIENCY_FREE", "EOA_ISSUED"): (
        "The workflow definition marks this step AUTOMATIC, but spec §4.3 forbids automatic approval. "
        "It therefore requires a Competent Authority decision."
    ),
}

STAGE_NOTES: dict[str, str] = {
    "PAYMENT_VERIFIED": "Payment was confirmed through the MOCK gateway only — no real transaction occurred.",
    "SELF_DISCLOSURE_VALIDATED": (
        "Automated self-disclosure validation is not implemented: no validation rules are published "
        "(spec §13.1 U6). Treat this stage as awaiting officer review."
    ),
    "DEFICIENCY_DETECTED": (
        "The Self-Disclosure workflow definition (v1) has no onward transition from this stage. "
        "Spec §4.2 says it should rejoin the standard scrutiny route; this needs a new, reviewed "
        "workflow definition version."
    ),
    "EVC_QUEUED": "EVC scheduling records and member assignments are delivered in Phase 4.",
}

# Rule families referenced by specific transitions (spec §3.2). They are looked
# up in the registry; only PUBLISHED + effective rules would ever be applied.
TRANSITION_RULE_REFS: dict[tuple[str, str], list[str]] = {
    ("REJECTED", "SAC_HEARING"): ["DL-APPEAL-7DAY-CH1", "DL-APPEAL-7DAY-CH2"],
}

PAYMENT_NOT_INITIATED = "NOT_INITIATED"
PAYMENT_MOCK_CONFIRMED = "MOCK_CONFIRMED"
PAYMENT_CONFIRMED_STATES = frozenset({PAYMENT_MOCK_CONFIRMED})

MAX_AUTOMATIC_CHAIN = 10


class WorkflowError(Exception):
    """Raised for rejected transitions. ``status_code`` maps to HTTP."""

    def __init__(self, status_code: int, message: str, *, code: str, details: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.details = details or {}


@dataclass
class TransitionDef:
    from_stage: str
    to_stage: str
    trigger: str
    role: str | None

    @property
    def key(self) -> tuple[str, str]:
        return (self.from_stage, self.to_stage)


@dataclass
class Definition:
    model: WorkflowDefinition
    stages: dict[str, dict]
    transitions: list[TransitionDef] = field(default_factory=list)

    def stage_type(self, stage: str) -> str:
        return self.stages.get(stage, {}).get("type", "intermediate")

    def stage_label(self, stage: str) -> str:
        return self.stages.get(stage, {}).get("label", stage.replace("_", " ").title())

    def outgoing(self, stage: str) -> list[TransitionDef]:
        return [t for t in self.transitions if t.from_stage == stage]

    def find(self, from_stage: str, to_stage: str) -> TransitionDef | None:
        for t in self.transitions:
            if t.from_stage == from_stage and t.to_stage == to_stage:
                return t
        return None

    def is_closing_stage(self, stage: str) -> bool:
        """Final/terminal stage with nothing after it: the case is closed."""
        return self.stage_type(stage) in ("final", "terminal") and not self.outgoing(stage)


def load_definition(model: WorkflowDefinition) -> Definition:
    raw = model.transitions or []
    trans = [
        TransitionDef(t["from"], t["to"], t.get("trigger", "MANUAL"), t.get("role"))
        for t in raw
    ]
    return Definition(model=model, stages=model.stages or {}, transitions=trans)


def requires_human(defn: Definition, t: TransitionDef) -> bool:
    return t.trigger != "AUTOMATIC" or defn.stage_type(t.to_stage) in HUMAN_DECISION_STAGE_TYPES


def effective_roles(defn: Definition, t: TransitionDef) -> frozenset[str]:
    """Roles allowed to perform a human transition."""
    if t.trigger == "AUTOMATIC" and defn.stage_type(t.to_stage) in HUMAN_DECISION_STAGE_TYPES:
        # Automatic-into-decision overridden by spec §4.3 → Competent Authority decides.
        return frozenset({R.COMPETENT_AUTHORITY})
    if not t.role:
        return frozenset()
    return ROLE_EQUIVALENTS.get(t.role, frozenset({t.role}))


def clock_owner_for(defn: Definition, stage: str) -> str | None:
    """Return 'AICTE' | 'INSTITUTION' | None (no clock) | 'COMPLETE'."""
    if stage == "DRAFT":
        return None
    if defn.is_closing_stage(stage):
        return "COMPLETE"
    if stage in INSTITUTION_CLOCK_STAGES:
        return "INSTITUTION"
    return "AICTE"


# --------------------------------------------------------------------------- #
# Loading helpers
# --------------------------------------------------------------------------- #

async def get_definition_for(db: AsyncSession, application: Application) -> tuple[Definition, WorkflowInstance | None]:
    inst = (await db.execute(
        select(WorkflowInstance).where(WorkflowInstance.application_id == application.id)
    )).scalar_one_or_none()
    if inst is not None:
        wf_id = inst.workflow_definition_id
    else:
        cat = (await db.execute(
            select(ApplicationCategory).where(ApplicationCategory.id == application.category_id)
        )).scalar_one()
        wf_id = cat.workflow_definition_id
    wf = (await db.execute(select(WorkflowDefinition).where(WorkflowDefinition.id == wf_id))).scalar_one()
    return load_definition(wf), inst


async def published_rule(db: AsyncSession, family_code: str, on: date) -> RegulatoryRule | None:
    """Only PUBLISHED rules effective on ``on`` are ever eligible (spec §9.B)."""
    q = (
        select(RegulatoryRule)
        .where(RegulatoryRule.rule_family_code == family_code)
        .where(RegulatoryRule.status == "PUBLISHED")
        .where(RegulatoryRule.effective_from <= on)
        .where((RegulatoryRule.effective_until.is_(None)) | (RegulatoryRule.effective_until >= on))
        .order_by(RegulatoryRule.version.desc())
    )
    return (await db.execute(q)).scalars().first()


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #

def _actor_can_reach(user, application: Application) -> bool:
    return scope_allows(
        application_scope(user), institution_id=application.institution_id, region_id=application.region_id
    )


def _precondition_failures(
    defn: Definition, application: Application, category_code: str, t: TransitionDef, remarks: str | None,
) -> list[str]:
    failures: list[str] = []
    if t.key == ("DRAFT", "SUBMITTED"):
        _, errors = validate_form_data(category_code, application.form_data, partial=False)
        if errors:
            failures.append(f"Application form is incomplete or invalid ({len(errors)} field(s)).")
    if t.to_stage == "PAYMENT_VERIFIED" and application.payment_status not in PAYMENT_CONFIRMED_STATES:
        failures.append("Payment has not been confirmed.")
    if t.to_stage in REMARKS_REQUIRED_TARGETS and requires_human(defn, t):
        if not remarks or len(remarks.strip()) < MIN_REMARKS_LENGTH:
            failures.append(f"Remarks of at least {MIN_REMARKS_LENGTH} characters are required for this action.")
    return failures


def available_actions(defn: Definition, application: Application, user, category_code: str) -> list[dict[str, Any]]:
    """Manual actions the given user may attempt from the current stage."""
    if application.status != "ACTIVE" or not _actor_can_reach(user, application):
        return []
    actions = []
    for t in defn.outgoing(application.stage):
        if not requires_human(defn, t) or user.role not in effective_roles(defn, t):
            continue
        blockers = [
            f for f in _precondition_failures(defn, application, category_code, t, remarks="x" * MIN_REMARKS_LENGTH)
        ]
        actions.append({
            "to_stage": t.to_stage,
            "to_stage_label": defn.stage_label(t.to_stage),
            "label": ACTION_LABELS.get(t.to_stage, f"Move to {defn.stage_label(t.to_stage)}"),
            "tone": ACTION_TONE.get(t.to_stage, "neutral"),
            "requires_remarks": t.to_stage in REMARKS_REQUIRED_TARGETS,
            "is_decision": t.to_stage in DECISION_OUTCOME_STAGES,
            "definition_trigger": t.trigger,
            "note": TRANSITION_NOTES.get(t.key),
            "blockers": blockers,
        })
    return actions


# --------------------------------------------------------------------------- #
# Core transition
# --------------------------------------------------------------------------- #

def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _apply_transition(
    db: AsyncSession,
    *,
    defn: Definition,
    instance: WorkflowInstance,
    application: Application,
    t: TransitionDef,
    actor,
    trigger_type: str,
    remarks: str | None,
    metadata: dict[str, Any],
) -> TransitionEvent:
    now = _now()
    from_version = application.version
    from_stage = application.stage

    # 1. Conditional update = optimistic lock. Zero rows → someone else moved it.
    values: dict[str, Any] = {"stage": t.to_stage, "version": from_version + 1, "updated_at": now}
    if from_stage == "DRAFT" and t.to_stage == "SUBMITTED":
        values["submitted_at"] = now
        values["submitted_by"] = actor.id if actor else None
    if t.to_stage in DECISION_OUTCOME_STAGES:
        values["decision"] = t.to_stage
        values["decided_at"] = now
        values["decision_remarks"] = remarks
    if defn.is_closing_stage(t.to_stage):
        values["status"] = "CLOSED"
    result = await db.execute(
        update(Application)
        .where(Application.id == application.id)
        .where(Application.version == from_version)
        .where(Application.stage == from_stage)
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise WorkflowError(409, "The application was changed by another action. Reload and try again.",
                            code="CONCURRENT_MODIFICATION")
    for k, v in values.items():
        set_committed_value(application, k, v)

    # 2. Workflow instance mirror.
    instance.current_stage = t.to_stage
    instance.version = application.version
    if defn.is_closing_stage(t.to_stage):
        instance.completed_at = now

    # 3. Stage history: close the open entry, open the new one.
    open_entry = (await db.execute(
        select(StageEntry).where(StageEntry.application_id == application.id).where(StageEntry.exited_at.is_(None))
    )).scalar_one_or_none()
    if open_entry is not None:
        open_entry.exited_at = now
        await db.flush()
    db.add(StageEntry(
        application_id=application.id, stage=t.to_stage, entered_at=now,
        entered_by=actor.id if actor else None, remarks=remarks,
    ))

    # 4. Transition event (sequence_no is UNIQUE per application).
    event = TransitionEvent(
        application_id=application.id, from_stage=from_stage, to_stage=t.to_stage,
        triggered_by=actor.id if actor else None, trigger_type=trigger_type,
        rule_family_code=None, rule_version=None,  # set only when a PUBLISHED rule authorises it
        remarks=remarks, sequence_no=from_version,
        actor_role=actor.role if actor else "system",
        metadata_={
            "workflow_definition": {"id": str(defn.model.id), "name": defn.model.name, "version": defn.model.version},
            "definition_trigger": t.trigger,
            **metadata,
        },
        occurred_at=now,
    )
    db.add(event)

    # 5. Clock events (append-only).
    prev_owner = clock_owner_for(defn, from_stage)
    new_owner = clock_owner_for(defn, t.to_stage)
    clock_meta = {"policy": CLOCK_POLICY_NOTE, "from_stage": from_stage, "to_stage": t.to_stage}
    if new_owner == "COMPLETE":
        if prev_owner not in (None, "COMPLETE"):
            db.add(ClockEvent(application_id=application.id, event_type="CLOCK_COMPLETE", clock_owner=prev_owner,
                              occurred_at=now, authorised_by=actor.id if actor else None,
                              reason=f"Case closed at {t.to_stage}", metadata_=clock_meta))
    elif prev_owner is None and new_owner is not None:
        db.add(ClockEvent(application_id=application.id, event_type="CLOCK_START", clock_owner=new_owner,
                          occurred_at=now, authorised_by=actor.id if actor else None,
                          reason=f"Entered {t.to_stage}", metadata_=clock_meta))
    elif prev_owner != new_owner and new_owner is not None:
        db.add(ClockEvent(application_id=application.id, event_type="CLOCK_TRANSFER", clock_owner=new_owner,
                          occurred_at=now, authorised_by=actor.id if actor else None,
                          reason=f"Responsibility moved to {new_owner} at {t.to_stage}", metadata_=clock_meta))

    # 6. Audit.
    await log_audit_event(
        db, actor_id=actor.id if actor else None, actor_role=actor.role if actor else "system",
        action="APPLICATION_TRANSITION", entity_type="Application", entity_id=application.id,
        changes={"from_stage": from_stage, "to_stage": t.to_stage, "trigger_type": trigger_type,
                 "version": {"old": from_version, "new": application.version},
                 "reference_number": application.reference_number},
    )
    await db.flush()
    return event


async def run_automatic_transitions(
    db: AsyncSession, *, defn: Definition, instance: WorkflowInstance, application: Application, category_code: str,
) -> list[TransitionEvent]:
    """Advance through AUTOMATIC steps whose preconditions hold.

    Never enters a human-decision stage. Stops at the first stage where the
    next automatic step is blocked or ambiguous.
    """
    events: list[TransitionEvent] = []
    for _ in range(MAX_AUTOMATIC_CHAIN):
        autos = [t for t in defn.outgoing(application.stage) if not requires_human(defn, t)]
        if len(autos) != 1:
            break
        t = autos[0]
        if _precondition_failures(defn, application, category_code, t, remarks=None):
            break
        meta: dict[str, Any] = {}
        if t.to_stage == "PAYMENT_VERIFIED":
            meta["mock"] = True
            meta["payment_reference"] = application.payment_reference
        if t.to_stage == "SELF_DISCLOSURE_VALIDATED":
            meta["validation_performed"] = False
            meta["note"] = STAGE_NOTES["SELF_DISCLOSURE_VALIDATED"]
        events.append(await _apply_transition(
            db, defn=defn, instance=instance, application=application, t=t, actor=None,
            trigger_type="AUTOMATIC",
            remarks=("[MOCK] " if meta.get("mock") else "") + "Automatic step per workflow definition",
            metadata=meta,
        ))
    return events


async def perform_transition(
    db: AsyncSession,
    *,
    application: Application,
    category_code: str,
    actor,
    to_stage: str,
    remarks: str | None,
    expected_version: int,
) -> list[TransitionEvent]:
    """Validate and execute a human-initiated transition, then any automatic follow-ups."""
    if not _actor_can_reach(actor, application):
        raise WorkflowError(403, "You do not have access to this application.", code="FORBIDDEN")
    if application.status != "ACTIVE":
        raise WorkflowError(409, f"Application is {application.status.lower()}; no further transitions.", code="NOT_ACTIVE")
    if expected_version != application.version:
        raise WorkflowError(409, "The application was changed since you loaded it. Reload and try again.",
                            code="STALE_VERSION",
                            details={"expected_version": expected_version, "current_version": application.version})
    if to_stage == application.stage:
        raise WorkflowError(409, f"Application is already at {to_stage}.", code="ALREADY_IN_STAGE")

    defn, instance = await get_definition_for(db, application)
    if instance is None:
        raise WorkflowError(500, "Workflow instance missing for application.", code="NO_INSTANCE")
    t = defn.find(application.stage, to_stage)
    if t is None:
        raise WorkflowError(422, f"Transition {application.stage} → {to_stage} is not permitted by the "
                                 f"'{defn.model.name}' workflow (v{defn.model.version}).",
                            code="INVALID_TRANSITION")
    if not requires_human(defn, t):
        raise WorkflowError(422, f"{application.stage} → {to_stage} is an automatic step and cannot be "
                                 f"triggered manually.", code="AUTOMATIC_ONLY")
    allowed = effective_roles(defn, t)
    if actor.role not in allowed:
        raise WorkflowError(403, f"Role '{actor.role}' may not perform this action "
                                 f"(allowed: {', '.join(sorted(allowed)) or 'none'}).", code="ROLE_NOT_ALLOWED")
    if actor.role in R.INSTITUTION_ROLES and actor.institution_id != application.institution_id:
        raise WorkflowError(403, "You do not have access to this application.", code="FORBIDDEN")

    failures = _precondition_failures(defn, application, category_code, t, remarks)
    if failures:
        raise WorkflowError(422, "Preconditions not met: " + " ".join(failures), code="PRECONDITION_FAILED",
                            details={"failures": failures})

    metadata: dict[str, Any] = {}
    if t.trigger == "AUTOMATIC":
        metadata["human_confirmation"] = (
            "Definition trigger AUTOMATIC overridden: spec §4.3 requires a human decision for this stage."
        )
    rule_refs = []
    for fam in TRANSITION_RULE_REFS.get(t.key, []):
        rule = await published_rule(db, fam, date.today())
        rule_refs.append({
            "rule_family_code": fam,
            "status": f"PUBLISHED v{rule.version} (evaluation arrives with the Phase 5 rule engine)" if rule
            else "NOT_PUBLISHED — not enforced",
        })
    if rule_refs:
        metadata["rule_refs"] = rule_refs

    if to_stage == "SUBMITTED":
        clean, _ = validate_form_data(category_code, application.form_data, partial=False)
        application.form_data = clean

    events = [await _apply_transition(
        db, defn=defn, instance=instance, application=application, t=t, actor=actor,
        trigger_type="MANUAL", remarks=(remarks or "").strip() or None, metadata=metadata,
    )]
    events += await run_automatic_transitions(
        db, defn=defn, instance=instance, application=application, category_code=category_code,
    )
    return events


# --------------------------------------------------------------------------- #
# Clock summary (derived from the append-only log)
# --------------------------------------------------------------------------- #

def summarise_clock(events: list[ClockEvent], now: datetime | None = None) -> dict[str, Any]:
    now = now or _now()
    totals = {"AICTE": 0.0, "INSTITUTION": 0.0, "HELD": 0.0}
    owner: str | None = None
    since: datetime | None = None
    completed = False
    for ev in sorted(events, key=lambda e: e.occurred_at):
        at = ev.occurred_at if ev.occurred_at.tzinfo else ev.occurred_at.replace(tzinfo=timezone.utc)
        if owner and since:
            totals[owner] = totals.get(owner, 0.0) + (at - since).total_seconds()
        if ev.event_type == "CLOCK_COMPLETE":
            owner, since, completed = None, None, True
        elif ev.event_type in ("CLOCK_START", "CLOCK_TRANSFER", "CLOCK_RESUME", "HOLD_END"):
            owner, since = ev.clock_owner, at
        elif ev.event_type in ("HOLD_START",):
            owner, since = "HELD", at
        elif ev.event_type == "CLOCK_PAUSE":
            owner, since = None, None
    if owner and since:
        totals[owner] = totals.get(owner, 0.0) + (now - since).total_seconds()
    return {
        "current_owner": owner,
        "completed": completed,
        "elapsed_seconds": {k: round(v) for k, v in totals.items()},
        "policy_note": CLOCK_POLICY_NOTE,
    }


async def ensure_instance(
    db: AsyncSession, application: Application, workflow_definition_id: uuid.UUID, created_by: uuid.UUID,
) -> WorkflowInstance:
    inst = WorkflowInstance(
        application_id=application.id, workflow_definition_id=workflow_definition_id,
        current_stage=application.stage, version=application.version,
    )
    db.add(inst)
    db.add(StageEntry(application_id=application.id, stage=application.stage, entered_by=created_by,
                      remarks="Draft created"))
    await db.flush()
    return inst

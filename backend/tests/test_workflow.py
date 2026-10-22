"""Phase 3: workflow engine — guards, routes, concurrency and persisted history."""
import asyncio

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models.application import StageEntry, TransitionEvent
from app.models.system import AuditEvent
from tests.conftest import login
from tests.helpers import (
    AUTHORITY, BUREAU, EVC_COORD, EVC_MEMBER, INST, SAC, SCRUTINY, SIGNATORY,
    act, create_draft, get, mock_pay, to_scrutiny,
)

REMARK = "Recorded with sufficient detail for the file."


async def _timeline(client, user, app):
    r = await get(client, user, app, "/timeline")
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------ submission ----

async def test_submit_requires_complete_form(client):
    app = await create_draft(client, form_data={"contact_person_name": "Only this"})
    body = await act(client, INST, app, "SUBMITTED", expected_status=422)
    assert body["detail"]["code"] == "PRECONDITION_FAILED"


async def test_submit_stops_at_payment_then_mock_payment_advances(client):
    app = await create_draft(client)
    app = await act(client, INST, app, "SUBMITTED")
    assert app["stage"] == "SUBMITTED" and app["submitted_at"]
    assert app["payment"]["status"] == "NOT_INITIATED"
    assert app["permissions"]["can_mock_pay"] is True
    assert app["clock"]["current_owner"] == "INSTITUTION"
    # automatic-only step cannot be forced manually
    body = await act(client, INST, app, "PAYMENT_VERIFIED", expected_status=422)
    assert body["detail"]["code"] == "AUTOMATIC_ONLY"
    paid = await mock_pay(client, app)
    assert paid["stage"] == "UNDER_SCRUTINY"
    assert paid["payment"]["status"] == "MOCK_CONFIRMED" and paid["payment"]["is_mock"] is True
    assert paid["payment"]["reference"].startswith("MOCK-")
    assert paid["clock"]["current_owner"] == "AICTE"
    tl = await _timeline(client, INST, paid)
    auto = [t for t in tl["transitions"] if t["trigger_type"] == "AUTOMATIC"]
    assert [(t["from_stage"], t["to_stage"]) for t in auto] == [
        ("SUBMITTED", "PAYMENT_VERIFIED"), ("PAYMENT_VERIFIED", "UNDER_SCRUTINY")]
    assert auto[0]["metadata"]["mock"] is True and auto[0]["remarks"].startswith("[MOCK]")
    # second payment rejected
    r = await client.post(f"/api/applications/{app['id']}/mock-payment", headers=await login(client, INST),
                          json={"expected_version": paid["version"]})
    assert r.status_code == 409


async def test_signatory_cannot_submit(client):
    app = await create_draft(client)
    r = await act(client, SIGNATORY, app, "SUBMITTED", expected_status=403)
    assert r["detail"]["code"] == "ROLE_NOT_ALLOWED"


# ---------------------------------------------------------------- guards ----

async def test_invalid_and_unauthorised_transitions(client):
    app = await to_scrutiny(client)
    body = await act(client, SCRUTINY, app, "APPROVED", REMARK, expected_status=422)
    assert body["detail"]["code"] == "INVALID_TRANSITION"
    body = await act(client, INST, app, "SCRUTINY_CLEAR", expected_status=403)
    assert body["detail"]["code"] == "ROLE_NOT_ALLOWED"
    body = await act(client, AUTHORITY, app, "SCRUTINY_CLEAR", expected_status=403)
    assert body["detail"]["code"] == "ROLE_NOT_ALLOWED"
    body = await act(client, SCRUTINY, app, "DEFICIENCY_NOTED", "short", expected_status=422)
    assert body["detail"]["code"] == "PRECONDITION_FAILED"
    body = await act(client, SCRUTINY, app, "UNDER_SCRUTINY", expected_status=409)
    assert body["detail"]["code"] == "ALREADY_IN_STAGE"
    # nothing was recorded by the failed attempts
    tl = await _timeline(client, SCRUTINY, app)
    assert tl["transitions"][-1]["to_stage"] == "UNDER_SCRUTINY"


async def test_stale_version_and_duplicate_request(client):
    app = await to_scrutiny(client)
    body = await act(client, SCRUTINY, app, "SCRUTINY_CLEAR", version=app["version"] - 1, expected_status=409)
    assert body["detail"]["code"] == "STALE_VERSION"
    done = await act(client, SCRUTINY, app, "SCRUTINY_CLEAR")
    assert done["stage"] == "EVC_QUEUED"  # automatic SCRUTINY_CLEAR → EVC_QUEUED (FULL route)
    # Replaying the identical request must not create a second transition
    await act(client, SCRUTINY, app, "SCRUTINY_CLEAR", expected_status=409)


async def test_concurrent_transitions_produce_single_consistent_history(client):
    app = await to_scrutiny(client)
    h = await login(client, SCRUTINY)

    async def attempt(to_stage, remarks=None):
        return await client.post(f"/api/applications/{app['id']}/transition", headers=h,
                                 json={"to_stage": to_stage, "remarks": remarks, "expected_version": app["version"]})

    results = await asyncio.gather(attempt("SCRUTINY_CLEAR"), attempt("DEFICIENCY_NOTED", REMARK),
                                   attempt("SCRUTINY_CLEAR"))
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) == 1, [r.text for r in results]
    assert all(c == 409 for c in codes if c != 200)

    async with async_session_factory() as db:
        seqs = (await db.execute(select(TransitionEvent.sequence_no)
                                 .where(TransitionEvent.application_id == app["id"]))).scalars().all()
        assert len(seqs) == len(set(seqs)), "duplicate sequence numbers"
        assert sorted(seqs) == list(range(1, len(seqs) + 1))
        open_entries = (await db.execute(select(func.count()).select_from(StageEntry)
                                         .where(StageEntry.application_id == app["id"])
                                         .where(StageEntry.exited_at.is_(None)))).scalar()
        assert open_entries == 1


# ---------------------------------------------------------------- routes ----

async def test_full_route_with_deficiency_loop_to_conditional_approval(client):
    """T-WF-01 / T-WF-04: FULL route goes Scrutiny → EVC → EC with human decision."""
    app = await to_scrutiny(client)
    app = await act(client, SCRUTINY, app, "DEFICIENCY_NOTED", "Faculty list incomplete for the proposed intake.")
    assert app["stage"] == "AWAITING_INSTITUTION_RESPONSE" and app["clock"]["current_owner"] == "INSTITUTION"
    app = await act(client, INST, app, "RESPONSE_RECEIVED", "Updated faculty list has been provided.")
    assert app["stage"] == "RE_SCRUTINY" and app["clock"]["current_owner"] == "AICTE"
    app = await act(client, SCRUTINY, app, "SCRUTINY_CLEAR")
    assert app["stage"] == "EVC_QUEUED"
    app = await act(client, EVC_COORD, app, "EVC_SCHEDULED")
    app = await act(client, EVC_MEMBER, app, "EVC_IN_PROGRESS")
    app = await act(client, EVC_MEMBER, app, "EVC_COMPLETED")
    app = await act(client, EVC_MEMBER, app, "REPORT_SUBMITTED")
    assert app["available_actions"] == [], "EVC member has no action at REPORT_SUBMITTED"
    bureau_view = (await get(client, BUREAU, app)).json()
    targets = {a["to_stage"]: a for a in bureau_view["available_actions"]}
    assert set(targets) == {"SHC_COMPLIANCE", "PLACED_BEFORE_EC"}
    assert targets["SHC_COMPLIANCE"]["note"]
    app = await act(client, BUREAU, app, "PLACED_BEFORE_EC")
    app = await act(client, AUTHORITY, app, "EC_DECISION")
    # the system never decides: no automatic move out of EC_DECISION
    assert app["stage"] == "EC_DECISION"
    await act(client, AUTHORITY, app, "APPROVED_WITH_CONDITIONS", expected_status=422)  # remarks required
    app = await act(client, AUTHORITY, app, "APPROVED_WITH_CONDITIONS",
                    "Approved subject to completing faculty recruitment within the session.")
    assert app["status"] == "CLOSED" and app["decision"] == "APPROVED_WITH_CONDITIONS"
    assert app["decided_at"] and app["available_actions"] == []
    assert app["clock"]["completed"] is True and app["clock"]["current_owner"] is None
    body = await act(client, AUTHORITY, app, "REJECTED", REMARK, expected_status=409)
    assert body["detail"]["code"] == "NOT_ACTIVE"

    tl = await _timeline(client, BUREAU, app)
    stages = [t["to_stage"] for t in tl["transitions"]]
    assert stages == [
        "SUBMITTED", "PAYMENT_VERIFIED", "UNDER_SCRUTINY", "DEFICIENCY_NOTED", "AWAITING_INSTITUTION_RESPONSE",
        "RESPONSE_RECEIVED", "RE_SCRUTINY", "SCRUTINY_CLEAR", "EVC_QUEUED", "EVC_SCHEDULED", "EVC_IN_PROGRESS",
        "EVC_COMPLETED", "REPORT_SUBMITTED", "PLACED_BEFORE_EC", "EC_DECISION", "APPROVED_WITH_CONDITIONS"]
    assert [t["sequence_no"] for t in tl["transitions"]] == list(range(1, len(stages) + 1))
    assert len(tl["stage_entries"]) == len(stages) + 1  # + initial DRAFT entry
    assert sum(1 for s in tl["stage_entries"] if s["exited_at"] is None) == 1
    assert [c["event_type"] for c in tl["clock_events"]][0] == "CLOCK_START"
    assert tl["clock_events"][-1]["event_type"] == "CLOCK_COMPLETE"
    decision = tl["transitions"][-1]
    assert decision["actor"]["role"] == "competent_authority" and decision["trigger_type"] == "MANUAL"

    async with async_session_factory() as db:
        audits = (await db.execute(select(func.count()).select_from(AuditEvent)
                                   .where(AuditEvent.entity_id == app["id"])
                                   .where(AuditEvent.action == "APPLICATION_TRANSITION"))).scalar()
    assert audits == len(stages)


async def test_scrutiny_only_route_cannot_enter_evc(client):
    """T-WF-03: a scrutiny-only category never reaches the EVC queue."""
    app = await to_scrutiny(client, "NAME_CHANGE")
    assert app["workflow"]["route_type"] == "SCRUTINY_ONLY"
    app = await act(client, SCRUTINY, app, "SCRUTINY_CLEAR")
    assert app["stage"] == "PLACED_BEFORE_EC"
    body = await act(client, EVC_COORD, app, "EVC_QUEUED", expected_status=422)
    assert body["detail"]["code"] == "INVALID_TRANSITION"


async def test_self_disclosure_never_auto_issues_eoa(client):
    """T-WF-02 with spec §4.3 override: EOA issuance needs the Competent Authority."""
    app = await to_scrutiny(client, "EOA_SELF_DISCLOSURE")
    assert app["stage"] == "SELF_DISCLOSURE_VALIDATED" and app["stage_note"]
    tl = await _timeline(client, INST, app)
    assert tl["transitions"][-1]["metadata"]["validation_performed"] is False
    app = await act(client, SCRUTINY, app, "DEFICIENCY_FREE")
    assert app["stage"] == "DEFICIENCY_FREE", "must not auto-advance into EOA_ISSUED"
    await act(client, SCRUTINY, app, "EOA_ISSUED", REMARK, expected_status=403)
    actions = (await get(client, AUTHORITY, app)).json()["available_actions"]
    assert [a["to_stage"] for a in actions] == ["EOA_ISSUED"] and actions[0]["definition_trigger"] == "AUTOMATIC"
    app = await act(client, AUTHORITY, app, "EOA_ISSUED", "Extension of approval issued on review of the disclosure.")
    assert app["status"] == "CLOSED" and app["decision"] == "EOA_ISSUED"
    tl = await _timeline(client, AUTHORITY, app)
    assert "human_confirmation" in tl["transitions"][-1]["metadata"]


async def test_scrutiny_only_rejection_closes_case(client):
    app = await to_scrutiny(client, "NAME_CHANGE")
    app = await act(client, SCRUTINY, app, "SCRUTINY_CLEAR")
    app = await act(client, AUTHORITY, app, "EC_DECISION")
    app = await act(client, AUTHORITY, app, "REJECTED", "Proposed name conflicts with an existing institution.")
    # Scrutiny-only definition v1 has no appeal path (flagged in the Phase 3 report).
    assert app["status"] == "CLOSED" and app["decision"] == "REJECTED"


async def test_full_route_rejection_appeal_to_final_rejection(client):
    """T-PROC-03: appeal goes to SAC; appeal-deadline rule is not published so not enforced."""
    app = await to_scrutiny(client)
    app = await act(client, SCRUTINY, app, "SCRUTINY_CLEAR")
    for user, stage in ((EVC_COORD, "EVC_SCHEDULED"), (EVC_MEMBER, "EVC_IN_PROGRESS"),
                        (EVC_MEMBER, "EVC_COMPLETED"), (EVC_MEMBER, "REPORT_SUBMITTED"),
                        (BUREAU, "PLACED_BEFORE_EC"), (AUTHORITY, "EC_DECISION")):
        app = await act(client, user, app, stage)
    app = await act(client, AUTHORITY, app, "REJECTED", "Infrastructure inadequate as per the EVC report.")
    assert app["status"] == "ACTIVE" and app["decision"] == "REJECTED"
    assert app["clock"]["current_owner"] == "INSTITUTION"
    inst_view = (await get(client, INST, app)).json()
    appeal = [a for a in inst_view["available_actions"] if a["to_stage"] == "SAC_HEARING"]
    assert appeal and "NOT enforce" in appeal[0]["note"]
    await act(client, SIGNATORY, app, "SAC_HEARING", REMARK, expected_status=403)
    app = await act(client, INST, app, "SAC_HEARING", "Appeal: additional lab space has since been completed.")
    tl = await _timeline(client, INST, app)
    refs = tl["transitions"][-1]["metadata"]["rule_refs"]
    assert {r["rule_family_code"] for r in refs} == {"DL-APPEAL-7DAY-CH1", "DL-APPEAL-7DAY-CH2"}
    assert all(r["status"].startswith("NOT_PUBLISHED") for r in refs)
    assert tl["transitions"][-1]["rule_family_code"] is None
    app = await act(client, SAC, app, "SAC_RECOMMENDATION", "SAC recommends upholding the rejection.")
    app = await act(client, AUTHORITY, app, "FINAL_REJECTION", "Rejection upheld after SAC hearing.")
    assert app["status"] == "CLOSED" and app["decision"] == "FINAL_REJECTION"


async def test_institution_sees_officials_by_role_only(client):
    app = await to_scrutiny(client)
    app = await act(client, SCRUTINY, app, "DEFICIENCY_NOTED", "Please provide the approved building plan.")
    inst_tl = await _timeline(client, INST, app)
    officer_tl = await _timeline(client, SCRUTINY, app)
    inst_def = next(t for t in inst_tl["transitions"] if t["to_stage"] == "DEFICIENCY_NOTED")
    off_def = next(t for t in officer_tl["transitions"] if t["to_stage"] == "DEFICIENCY_NOTED")
    assert inst_def["actor"] == {"name": None, "role": "scrutiny_officer"}
    assert off_def["actor"]["name"] == "Scrutiny Officer"
    own = next(t for t in inst_tl["transitions"] if t["to_stage"] == "SUBMITTED")
    assert own["actor"]["name"] == "Institution User"

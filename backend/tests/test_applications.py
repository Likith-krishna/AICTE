"""Phase 3: application creation, scoping, drafts and listing."""
import uuid

from tests.conftest import login
from tests.helpers import (
    ADMIN, AUDITOR, BUREAU, INST, INST2, OFFICER, RULE_ADMIN, SCRUTINY, SCRUTINY_SR, SIGNATORY,
    academic_year_id, act, category_id, create_draft, full_form, get, to_scrutiny,
)


async def _list(client, user, **params):
    r = await client.get("/api/applications", headers=await login(client, user), params=params)
    return r


# ---------------------------------------------------------------- creation --

async def test_institution_applicant_creates_draft(client):
    app = await create_draft(client, form_data={"contact_person_name": "Partial"})
    assert app["stage"] == "DRAFT" and app["status"] == "ACTIVE" and app["version"] == 1
    assert app["reference_number"].startswith("FG/") and "/NR/" in app["reference_number"]
    assert app["institution"]["pid"] == "AICTE-NR-2024-0001"
    assert app["workflow"]["route_type"] == "FULL"
    assert app["permissions"]["can_edit"] is True
    assert app["form_errors"], "incomplete draft must report missing fields"
    assert app["created_at"].endswith("+00:00"), "timestamps must carry a UTC offset"


async def test_client_supplied_institution_is_ignored(client):
    r = await client.post("/api/applications", headers=await login(client, INST), json={
        "category_id": await category_id(client, "NAME_CHANGE"),
        "academic_year_id": await academic_year_id(client),
        "institution_id": str(uuid.uuid4()), "region_id": str(uuid.uuid4()),
    })
    assert r.status_code == 201
    assert r.json()["institution"]["pid"] == "AICTE-NR-2024-0001"
    assert r.json()["region"]["code"] == "NR"


async def test_non_applicant_roles_cannot_create(client):
    body = {"category_id": await category_id(client, "NAME_CHANGE"), "academic_year_id": await academic_year_id(client)}
    for user in (SCRUTINY, ADMIN, BUREAU, SIGNATORY):
        r = await client.post("/api/applications", headers=await login(client, user), json=body)
        assert r.status_code == 403, user


async def test_create_validates_category_year_and_form(client):
    h = await login(client, INST)
    ay = await academic_year_id(client)
    r = await client.post("/api/applications", headers=h, json={"category_id": str(uuid.uuid4()), "academic_year_id": ay})
    assert r.status_code == 422
    cat = await category_id(client, "INCREASE_INTAKE")
    r = await client.post("/api/applications", headers=h, json={"category_id": cat, "academic_year_id": str(uuid.uuid4())})
    assert r.status_code == 422
    r = await client.post("/api/applications", headers=h, json={
        "category_id": cat, "academic_year_id": ay,
        "form_data": {"current_intake": "sixty", "not_a_field": 1, "contact_email": "bad"}})
    assert r.status_code == 422
    errs = r.json()["detail"]["field_errors"]
    assert set(errs) == {"current_intake", "not_a_field", "contact_email"}


async def test_form_schema_endpoint(client):
    r = await client.get("/api/applications/form-schema/INCREASE_INTAKE", headers=await login(client, INST))
    body = r.json()
    assert r.status_code == 200 and body["verification_status"] == "PROTOTYPE_DESCRIPTIVE_FIELDS"
    names = [f["name"] for f in body["fields"]]
    assert "proposed_intake" in names and names[-1] == "declaration_accepted"
    r = await client.get("/api/applications/form-schema/NOPE", headers=await login(client, INST))
    assert r.status_code == 404


# ------------------------------------------------------------ draft editing --

async def test_draft_update_with_version_check_and_audit(client):
    app = await create_draft(client, form_data={})
    h = await login(client, INST)
    r = await client.patch(f"/api/applications/{app['id']}", headers=h,
                           json={"form_data": full_form("INCREASE_INTAKE"), "expected_version": 1})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["version"] == 2 and updated["form_errors"] == {}
    r = await client.patch(f"/api/applications/{app['id']}", headers=h,
                           json={"form_data": {}, "expected_version": 1})
    assert r.status_code == 409


async def test_cross_field_validation_on_submit(client):
    form = full_form("INCREASE_INTAKE") | {"proposed_intake": 30}
    app = await create_draft(client, form_data=form)
    body = await act(client, INST, app, "SUBMITTED", expected_status=422)
    assert body["detail"]["code"] == "PRECONDITION_FAILED"
    assert "proposed_intake" in app["form_errors"]


async def test_withdraw_draft_keeps_record(client):
    app = await create_draft(client)
    r = await client.post(f"/api/applications/{app['id']}/withdraw", headers=await login(client, INST),
                          json={"expected_version": app["version"], "remarks": "Created by mistake"})
    assert r.status_code == 200 and r.json()["status"] == "WITHDRAWN"
    w = r.json()
    r = await client.patch(f"/api/applications/{app['id']}", headers=await login(client, INST),
                           json={"form_data": {}, "expected_version": w["version"]})
    assert r.status_code == 409
    await act(client, INST, w, "SUBMITTED", expected_status=409)


# ------------------------------------------------------------- isolation ----

async def test_institution_isolation(client):
    app = await create_draft(client)
    assert (await get(client, INST2, app)).status_code == 403
    assert (await get(client, INST, app)).status_code == 200
    assert (await get(client, SIGNATORY, app)).status_code == 200
    ids = {i["id"] for i in (await _list(client, INST2, page_size=100)).json()["items"]}
    assert app["id"] not in ids
    r = await client.get(f"/api/applications/{uuid.uuid4()}", headers=await login(client, INST2))
    assert r.status_code == 403


async def test_drafts_are_private_to_institution(client):
    app = await create_draft(client)
    for user in (SCRUTINY, BUREAU):
        assert (await get(client, user, app)).status_code == 403
        ids = {i["id"] for i in (await _list(client, user, page_size=100)).json()["items"]}
        assert app["id"] not in ids


async def test_regional_isolation_after_submission(client):
    app = await to_scrutiny(client)
    assert app["stage"] == "UNDER_SCRUTINY"
    for user in (SCRUTINY, OFFICER, BUREAU, AUDITOR):
        assert (await get(client, user, app)).status_code == 200, user
    assert (await get(client, SCRUTINY_SR, app)).status_code == 403
    ids = {i["id"] for i in (await _list(client, SCRUTINY_SR, page_size=100)).json()["items"]}
    assert app["id"] not in ids
    await act(client, SCRUTINY_SR, app, "SCRUTINY_CLEAR", expected_status=403)


async def test_admin_roles_cannot_read_application_content(client):
    app = await to_scrutiny(client)
    for user in (ADMIN, RULE_ADMIN):
        assert (await _list(client, user)).status_code == 403
        assert (await get(client, user, app)).status_code == 403
    stats = (await client.get("/api/dashboard/stats", headers=await login(client, ADMIN))).json()
    assert stats["total_applications"] >= 1, "aggregate counts remain visible to administrators"


async def test_list_filters_search_and_needs_my_action(client):
    app = await to_scrutiny(client)
    r = await _list(client, SCRUTINY, search=app["reference_number"])
    assert [i["id"] for i in r.json()["items"]] == [app["id"]]
    item = r.json()["items"][0]
    assert item["needs_my_action"] is True and item["stage_label"] == "Under Scrutiny"
    mine = {i["id"] for i in (await _list(client, SCRUTINY, needs_my_action="true", page_size=100)).json()["items"]}
    assert app["id"] in mine
    theirs = {i["id"] for i in (await _list(client, BUREAU, needs_my_action="true", page_size=100)).json()["items"]}
    assert app["id"] not in theirs
    r = await _list(client, SCRUTINY, stage="APPROVED")
    assert all(i["stage"] == "APPROVED" for i in r.json()["items"])
    r = await _list(client, INST, page=1, page_size=2, sort_by="reference_number", sort_dir="asc")
    body = r.json()
    assert len(body["items"]) <= 2 and body["total"] >= 2 and body["pages"] >= 1

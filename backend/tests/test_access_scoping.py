"""Regression tests for scoping fixes made at the start of Phase 3 (spec §2.1, T-AC-01/02)."""
import uuid

from tests.conftest import login
from tests.helpers import ADMIN, INST, INST2, SCRUTINY, SCRUTINY_SR, SIGNATORY


async def _institutions(client, user):
    r = await client.get("/api/institutions", headers=await login(client, user))
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def test_signatory_sees_only_own_institution(client):
    items = await _institutions(client, SIGNATORY)
    assert [i["pid"] for i in items] == ["AICTE-NR-2024-0001"]


async def test_institution_user_cannot_read_other_institution(client):
    other = next(i for i in await _institutions(client, ADMIN) if i["pid"] == "AICTE-SR-2024-0002")
    r = await client.get(f"/api/institutions/{other['id']}", headers=await login(client, INST))
    assert r.status_code == 403


async def test_scoped_user_gets_403_for_unknown_institution_id(client):
    r = await client.get(f"/api/institutions/{uuid.uuid4()}", headers=await login(client, INST2))
    assert r.status_code == 403
    r = await client.get(f"/api/institutions/{uuid.uuid4()}", headers=await login(client, ADMIN))
    assert r.status_code == 404


async def test_scrutiny_officer_is_region_scoped_for_institutions(client):
    assert {i["pid"] for i in await _institutions(client, SCRUTINY)} == {"AICTE-NR-2024-0001"}
    assert {i["pid"] for i in await _institutions(client, SCRUTINY_SR)} == {"AICTE-SR-2024-0002"}


async def test_regional_user_without_region_sees_nothing(client):
    admin = await login(client, ADMIN)
    email = f"noregion-{uuid.uuid4().hex[:6]}@flowguard.gov.in"
    r = await client.post("/api/users", headers=admin, json={
        "email": email, "password": "Demo@123", "full_name": "No Region", "role": "regional_officer"})
    assert r.status_code == 201, r.text
    assert await _institutions(client, email) == []
    r = await client.get("/api/applications", headers=await login(client, email))
    assert r.status_code == 200 and r.json()["total"] == 0


async def test_users_endpoint_accepts_all_seeded_roles_and_rejects_unknown(client):
    admin = await login(client, ADMIN)
    r = await client.post("/api/users", headers=admin, json={
        "email": f"sig-{uuid.uuid4().hex[:6]}@demo.ac.in", "password": "Demo@123",
        "full_name": "Sig", "role": "institution_signatory"})
    assert r.status_code == 201, r.text
    r = await client.post("/api/users", headers=admin, json={
        "email": f"x-{uuid.uuid4().hex[:6]}@demo.ac.in", "password": "Demo@123",
        "full_name": "X", "role": "evc_chair"})
    assert r.status_code == 400


async def test_register_validates_role_and_is_admin_only(client):
    body = {"email": f"r-{uuid.uuid4().hex[:6]}@x.in", "password": "Demo@123", "full_name": "R", "role": "superuser"}
    r = await client.post("/api/auth/register", headers=await login(client, ADMIN), json=body)
    assert r.status_code == 400
    r = await client.post("/api/auth/register", headers=await login(client, INST), json={**body, "role": "system_admin"})
    assert r.status_code == 403

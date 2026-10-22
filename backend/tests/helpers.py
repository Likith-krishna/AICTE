"""Shared helpers for API tests."""
from httpx import AsyncClient

from tests.conftest import login

INST = "institution@demo.ac.in"          # Demo Institute of Technology (NR)
INST2 = "institution2@demo.ac.in"        # Southern Demo College of Engineering (SR)
SIGNATORY = "signatory@demo.ac.in"       # institution_signatory, DIT (NR)
SCRUTINY = "scrutiny@flowguard.gov.in"   # NR
SCRUTINY_SR = "scrutiny.sr@flowguard.gov.in"
OFFICER = "officer@flowguard.gov.in"     # regional_officer NR
EVC_COORD = "evc@flowguard.gov.in"
EVC_MEMBER = "evcmember@flowguard.gov.in"
BUREAU = "bureau@flowguard.gov.in"
AUTHORITY = "authority@flowguard.gov.in"
SAC = "sac@flowguard.gov.in"
ADMIN = "admin@flowguard.gov.in"
RULE_ADMIN = "ruleadmin@flowguard.gov.in"
AUDITOR = "auditor@flowguard.gov.in"

COMMON = {
    "contact_person_name": "Dr. Asha Rao",
    "contact_person_designation": "Principal",
    "contact_email": "principal@dit.ac.in",
    "contact_phone": "+91 11 2345 6789",
    "request_summary": "Request for consideration under the selected category for the coming academic year.",
    "declaration_accepted": True,
}
CATEGORY_EXTRA = {
    "INCREASE_INTAKE": {"programme_name": "Engineering & Technology", "course_name": "Computer Science",
                        "level": "Under Graduate", "current_intake": 60, "proposed_intake": 120},
    "NAME_CHANGE": {"current_name": "Demo Institute of Technology", "proposed_name": "Demo Institute of Engineering"},
}

_categories: dict[str, str] = {}
_years: list[str] = []


async def category_id(client: AsyncClient, code: str) -> str:
    if not _categories:
        r = await client.get("/api/applications/categories", headers=await login(client, INST))
        assert r.status_code == 200
        _categories.update({c["code"]: c["id"] for c in r.json()})
    return _categories[code]


async def academic_year_id(client: AsyncClient) -> str:
    if not _years:
        r = await client.get("/api/applications/academic-years", headers=await login(client, INST))
        _years.extend(y["id"] for y in r.json())
    return _years[0]


def full_form(code: str) -> dict:
    return {**COMMON, **CATEGORY_EXTRA.get(code, {})}


async def create_draft(client: AsyncClient, code: str = "INCREASE_INTAKE", *, user: str = INST,
                       form_data: dict | None = None) -> dict:
    r = await client.post("/api/applications", headers=await login(client, user), json={
        "category_id": await category_id(client, code),
        "academic_year_id": await academic_year_id(client),
        "form_data": full_form(code) if form_data is None else form_data,
    })
    assert r.status_code == 201, r.text
    return r.json()


async def act(client: AsyncClient, user: str, app: dict, to_stage: str, remarks: str | None = None,
              expected_status: int = 200, version: int | None = None) -> dict:
    r = await client.post(f"/api/applications/{app['id']}/transition", headers=await login(client, user), json={
        "to_stage": to_stage, "remarks": remarks,
        "expected_version": app["version"] if version is None else version,
    })
    assert r.status_code == expected_status, f"{to_stage}: {r.status_code} {r.text}"
    return r.json()


async def mock_pay(client: AsyncClient, app: dict, user: str = INST) -> dict:
    r = await client.post(f"/api/applications/{app['id']}/mock-payment", headers=await login(client, user),
                          json={"expected_version": app["version"]})
    assert r.status_code == 200, r.text
    return r.json()


async def to_scrutiny(client: AsyncClient, code: str = "INCREASE_INTAKE", user: str = INST) -> dict:
    app = await create_draft(client, code, user=user)
    app = await act(client, user, app, "SUBMITTED")
    return await mock_pay(client, app, user=user)


async def get(client: AsyncClient, user: str, app: dict, suffix: str = ""):
    return await client.get(f"/api/applications/{app['id']}{suffix}", headers=await login(client, user))

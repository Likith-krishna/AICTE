"""Seed the database with demo data for development."""
import asyncio
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.migrate import migrate
from app.core.security import hash_password
from app.models.user import User, Role
from app.models.institution import Region, Institution
from app.models.application import AcademicYear, WorkflowDefinition, ApplicationCategory
import app.models  # noqa: F401


REGIONS = [
    ("NR", "Northern Region"),
    ("SR", "Southern Region"),
    ("WR", "Western Region"),
    ("ER", "Eastern Region"),
    ("CR", "Central Region"),
    ("NWR", "North-Western Region"),
    ("SWR", "South-Western Region"),
]

ROLES = [
    ("institution_applicant", "Institution Applicant"),
    ("institution_signatory", "Authorised Signatory"),
    ("regional_officer", "Regional Officer"),
    ("scrutiny_officer", "Scrutiny Officer"),
    ("regional_coordinator", "Regional Coordinator"),
    ("bureau_officer", "Regulation Bureau Officer"),
    ("evc_coordinator", "EVC Coordinator"),
    ("evc_member", "EVC Member"),
    ("sac_shc_member", "SAC/SHC Committee Member"),
    ("competent_authority", "Competent Authority"),
    ("compliance_officer", "Compliance Verification Officer"),
    ("system_admin", "System Administrator"),
    ("rule_admin", "Regulatory Rule Administrator"),
    ("audit_reviewer", "Audit/Read-Only Reviewer"),
]

WORKFLOW_FULL = {
    "name": "Full Route (Scrutiny + EVC + AA)",
    "route_type": "FULL",
    "stages": {
        "DRAFT": {"label": "Draft", "type": "initial"},
        "SUBMITTED": {"label": "Submitted", "type": "intermediate"},
        "PAYMENT_VERIFIED": {"label": "Payment Verified", "type": "intermediate"},
        "UNDER_SCRUTINY": {"label": "Under Scrutiny", "type": "intermediate"},
        "SCRUTINY_CLEAR": {"label": "Scrutiny Clear", "type": "intermediate"},
        "DEFICIENCY_NOTED": {"label": "Deficiency Noted", "type": "intermediate"},
        "AWAITING_INSTITUTION_RESPONSE": {"label": "Awaiting Institution Response", "type": "intermediate"},
        "RESPONSE_RECEIVED": {"label": "Response Received", "type": "intermediate"},
        "RE_SCRUTINY": {"label": "Re-Scrutiny", "type": "intermediate"},
        "EVC_QUEUED": {"label": "EVC Queued", "type": "intermediate"},
        "EVC_SCHEDULED": {"label": "EVC Scheduled", "type": "intermediate"},
        "EVC_IN_PROGRESS": {"label": "EVC In Progress", "type": "intermediate"},
        "EVC_COMPLETED": {"label": "EVC Completed", "type": "intermediate"},
        "REPORT_SUBMITTED": {"label": "EVC Report Submitted", "type": "intermediate"},
        "SHC_COMPLIANCE": {"label": "SHC Compliance", "type": "intermediate"},
        "SHC_RECOMMENDATION": {"label": "SHC Recommendation", "type": "intermediate"},
        "PLACED_BEFORE_EC": {"label": "Placed Before EC", "type": "intermediate"},
        "EC_DECISION": {"label": "EC Decision", "type": "decision"},
        "APPROVED": {"label": "Approved", "type": "final"},
        "APPROVED_WITH_CONDITIONS": {"label": "Approved with Conditions", "type": "final"},
        "REJECTED": {"label": "Rejected", "type": "final"},
        "SAC_HEARING": {"label": "SAC Hearing", "type": "intermediate"},
        "SAC_RECOMMENDATION": {"label": "SAC Recommendation", "type": "intermediate"},
        "FINAL_REJECTION": {"label": "Final Rejection", "type": "terminal"},
    },
    "transitions": [
        {"from": "DRAFT", "to": "SUBMITTED", "trigger": "MANUAL", "role": "institution_applicant"},
        {"from": "SUBMITTED", "to": "PAYMENT_VERIFIED", "trigger": "AUTOMATIC"},
        {"from": "PAYMENT_VERIFIED", "to": "UNDER_SCRUTINY", "trigger": "AUTOMATIC"},
        {"from": "UNDER_SCRUTINY", "to": "SCRUTINY_CLEAR", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "UNDER_SCRUTINY", "to": "DEFICIENCY_NOTED", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "DEFICIENCY_NOTED", "to": "AWAITING_INSTITUTION_RESPONSE", "trigger": "AUTOMATIC"},
        {"from": "AWAITING_INSTITUTION_RESPONSE", "to": "RESPONSE_RECEIVED", "trigger": "MANUAL", "role": "institution_applicant"},
        {"from": "RESPONSE_RECEIVED", "to": "RE_SCRUTINY", "trigger": "AUTOMATIC"},
        {"from": "RE_SCRUTINY", "to": "SCRUTINY_CLEAR", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "RE_SCRUTINY", "to": "DEFICIENCY_NOTED", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "SCRUTINY_CLEAR", "to": "EVC_QUEUED", "trigger": "AUTOMATIC"},
        {"from": "EVC_QUEUED", "to": "EVC_SCHEDULED", "trigger": "MANUAL", "role": "evc_coordinator"},
        {"from": "EVC_SCHEDULED", "to": "EVC_IN_PROGRESS", "trigger": "MANUAL", "role": "evc_member"},
        {"from": "EVC_IN_PROGRESS", "to": "EVC_COMPLETED", "trigger": "MANUAL", "role": "evc_member"},
        {"from": "EVC_COMPLETED", "to": "REPORT_SUBMITTED", "trigger": "MANUAL", "role": "evc_member"},
        {"from": "REPORT_SUBMITTED", "to": "SHC_COMPLIANCE", "trigger": "MANUAL", "role": "bureau_officer"},
        {"from": "REPORT_SUBMITTED", "to": "PLACED_BEFORE_EC", "trigger": "MANUAL", "role": "bureau_officer"},
        {"from": "SHC_COMPLIANCE", "to": "SHC_RECOMMENDATION", "trigger": "MANUAL", "role": "sac_shc_member"},
        {"from": "SHC_RECOMMENDATION", "to": "PLACED_BEFORE_EC", "trigger": "AUTOMATIC"},
        {"from": "PLACED_BEFORE_EC", "to": "EC_DECISION", "trigger": "MANUAL", "role": "competent_authority"},
        {"from": "EC_DECISION", "to": "APPROVED", "trigger": "MANUAL", "role": "competent_authority"},
        {"from": "EC_DECISION", "to": "APPROVED_WITH_CONDITIONS", "trigger": "MANUAL", "role": "competent_authority"},
        {"from": "EC_DECISION", "to": "REJECTED", "trigger": "MANUAL", "role": "competent_authority"},
        {"from": "REJECTED", "to": "SAC_HEARING", "trigger": "MANUAL", "role": "institution_applicant"},
        {"from": "SAC_HEARING", "to": "SAC_RECOMMENDATION", "trigger": "MANUAL", "role": "sac_shc_member"},
        {"from": "SAC_RECOMMENDATION", "to": "APPROVED", "trigger": "MANUAL", "role": "competent_authority"},
        {"from": "SAC_RECOMMENDATION", "to": "FINAL_REJECTION", "trigger": "MANUAL", "role": "competent_authority"},
    ],
}

WORKFLOW_SCRUTINY_ONLY = {
    "name": "Scrutiny Only Route",
    "route_type": "SCRUTINY_ONLY",
    "stages": {
        "DRAFT": {"label": "Draft", "type": "initial"},
        "SUBMITTED": {"label": "Submitted", "type": "intermediate"},
        "PAYMENT_VERIFIED": {"label": "Payment Verified", "type": "intermediate"},
        "UNDER_SCRUTINY": {"label": "Under Scrutiny", "type": "intermediate"},
        "SCRUTINY_CLEAR": {"label": "Scrutiny Clear", "type": "intermediate"},
        "DEFICIENCY_NOTED": {"label": "Deficiency Noted", "type": "intermediate"},
        "AWAITING_INSTITUTION_RESPONSE": {"label": "Awaiting Response", "type": "intermediate"},
        "RESPONSE_RECEIVED": {"label": "Response Received", "type": "intermediate"},
        "RE_SCRUTINY": {"label": "Re-Scrutiny", "type": "intermediate"},
        "PLACED_BEFORE_EC": {"label": "Placed Before EC", "type": "intermediate"},
        "EC_DECISION": {"label": "EC Decision", "type": "decision"},
        "APPROVED": {"label": "Approved", "type": "final"},
        "REJECTED": {"label": "Rejected", "type": "final"},
    },
    "transitions": [
        {"from": "DRAFT", "to": "SUBMITTED", "trigger": "MANUAL", "role": "institution_applicant"},
        {"from": "SUBMITTED", "to": "PAYMENT_VERIFIED", "trigger": "AUTOMATIC"},
        {"from": "PAYMENT_VERIFIED", "to": "UNDER_SCRUTINY", "trigger": "AUTOMATIC"},
        {"from": "UNDER_SCRUTINY", "to": "SCRUTINY_CLEAR", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "UNDER_SCRUTINY", "to": "DEFICIENCY_NOTED", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "DEFICIENCY_NOTED", "to": "AWAITING_INSTITUTION_RESPONSE", "trigger": "AUTOMATIC"},
        {"from": "AWAITING_INSTITUTION_RESPONSE", "to": "RESPONSE_RECEIVED", "trigger": "MANUAL", "role": "institution_applicant"},
        {"from": "RESPONSE_RECEIVED", "to": "RE_SCRUTINY", "trigger": "AUTOMATIC"},
        {"from": "RE_SCRUTINY", "to": "SCRUTINY_CLEAR", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "RE_SCRUTINY", "to": "DEFICIENCY_NOTED", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "SCRUTINY_CLEAR", "to": "PLACED_BEFORE_EC", "trigger": "AUTOMATIC"},
        {"from": "PLACED_BEFORE_EC", "to": "EC_DECISION", "trigger": "MANUAL", "role": "competent_authority"},
        {"from": "EC_DECISION", "to": "APPROVED", "trigger": "MANUAL", "role": "competent_authority"},
        {"from": "EC_DECISION", "to": "REJECTED", "trigger": "MANUAL", "role": "competent_authority"},
    ],
}

WORKFLOW_SELF_DISCLOSURE = {
    "name": "Self-Disclosure Route",
    "route_type": "SELF_DISCLOSURE",
    "stages": {
        "DRAFT": {"label": "Draft", "type": "initial"},
        "SUBMITTED": {"label": "Submitted", "type": "intermediate"},
        "PAYMENT_VERIFIED": {"label": "Payment Verified", "type": "intermediate"},
        "SELF_DISCLOSURE_VALIDATED": {"label": "Self-Disclosure Validated", "type": "intermediate"},
        "DEFICIENCY_FREE": {"label": "Deficiency Free", "type": "intermediate"},
        "DEFICIENCY_DETECTED": {"label": "Deficiency Detected", "type": "intermediate"},
        "EOA_ISSUED": {"label": "EoA Issued", "type": "final"},
    },
    "transitions": [
        {"from": "DRAFT", "to": "SUBMITTED", "trigger": "MANUAL", "role": "institution_applicant"},
        {"from": "SUBMITTED", "to": "PAYMENT_VERIFIED", "trigger": "AUTOMATIC"},
        {"from": "PAYMENT_VERIFIED", "to": "SELF_DISCLOSURE_VALIDATED", "trigger": "AUTOMATIC"},
        {"from": "SELF_DISCLOSURE_VALIDATED", "to": "DEFICIENCY_FREE", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "SELF_DISCLOSURE_VALIDATED", "to": "DEFICIENCY_DETECTED", "trigger": "MANUAL", "role": "scrutiny_officer"},
        {"from": "DEFICIENCY_FREE", "to": "EOA_ISSUED", "trigger": "AUTOMATIC"},
    ],
}

APPLICATION_CATEGORIES = [
    ("NEW_INSTITUTION", "New Technical Institution", 1, False, True, True, "AA", "FULL"),
    ("EOA_SELF_DISCLOSURE", "Extension of Approval (Self-Disclosure)", 1, True, False, False, "-", "SELF_DISCLOSURE"),
    ("EOA_SCRUTINY", "Extension of Approval (Scrutiny)", 1, False, True, True, "AA", "FULL"),
    ("INCREASE_INTAKE", "Increase in Intake / Additional Course", 1, False, True, True, "AA", "FULL"),
    ("NEW_PROGRAMME", "Introduction of New Programme/Level", 1, False, True, True, "AA", "FULL"),
    ("CHANGE_OF_SITE", "Change of Site/Location", 1, False, True, True, "AA", "FULL"),
    ("MERGER", "Merger of Institutions", 1, False, True, True, "AA", "FULL"),
    ("BREAK_IN_EOA", "Break in EoA / Restoration / Hibernation", 1, False, True, True, "AA", "FULL"),
    ("DIPLOMA_DEGREE_CONVERSION", "Diploma-Degree Conversion", 1, False, True, True, "AA", "FULL"),
    ("COLLABORATION_TWINNING", "Collaboration & Twinning Programme", 1, False, True, True, "AA", "FULL"),
    ("INTEGRATED_DUAL_DEGREE", "Integrated/Dual Degree Programme", 1, False, True, True, "AA", "FULL"),
    ("FPM_INTRODUCTION", "FPM Introduction/Continuation", 1, False, True, True, "AA", "FULL"),
    ("DEEMED_UNIVERSITY", "Deemed University Conversion", 1, False, True, True, "AA", "FULL"),
    ("ODL_OL_COURSES", "ODL/OL Courses", 1, False, True, True, "AA", "FULL"),
    ("NRI_SEATS", "NRI Seats Introduction/Continuation", 2, True, False, False, "-", "SELF_DISCLOSURE"),
    ("NAME_CHANGE", "Institution/University/Board Name Change", 2, False, True, False, "-", "SCRUTINY_ONLY"),
    ("FN_OCI_SEATS", "FN/OCI/Gulf Children Seats", 2, False, True, False, "-", "SCRUTINY_ONLY"),
    ("COURSE_NAME_CHANGE", "Course Name Change/Merger/Reduction", 2, False, True, False, "-", "SCRUTINY_ONLY"),
    ("CLOSURE_INSTITUTION", "Closure of Institution", 2, False, True, False, "-", "SCRUTINY_ONLY"),
    ("CLOSURE_PROGRAMME", "Closure of Programme(s)/Course(s)", 2, False, True, False, "-", "SCRUTINY_ONLY"),
    ("WOMEN_COED_CONVERSION", "Women's to Co-ed Conversion", 2, False, True, False, "-", "SCRUTINY_ONLY"),
    ("CHANGE_BANK_DETAILS", "Change Bank Details", 2, False, True, False, "-", "SCRUTINY_ONLY"),
    ("CHANGE_TRUST_NAME", "Change Trust/Society/Company Name", 2, False, True, False, "-", "SCRUTINY_ONLY"),
]


# --------------------------------------------------------------------------- #
# Phase 3 demo additions (additive + idempotent: each row is created only if
# missing, so existing databases keep all data and identifiers).
# --------------------------------------------------------------------------- #
PHASE3_INSTITUTIONS = [
    # pid, name, region, state, city
    ("AICTE-SR-2024-0002", "Southern Demo College of Engineering", "SR", "Karnataka", "Bengaluru"),
]

PHASE3_USERS = [
    # email, name, role, institution pid, region code
    ("signatory@demo.ac.in", "Authorised Signatory (DIT)", "institution_signatory", "AICTE-NR-2024-0001", "NR"),
    ("institution2@demo.ac.in", "Institution User (SDCE)", "institution_applicant", "AICTE-SR-2024-0002", "SR"),
    ("evcmember@flowguard.gov.in", "EVC Member", "evc_member", None, "NR"),
    ("sac@flowguard.gov.in", "SAC/SHC Committee Member", "sac_shc_member", None, None),
    ("coordinator@flowguard.gov.in", "Regional Coordinator", "regional_coordinator", None, "NR"),
    ("scrutiny.sr@flowguard.gov.in", "Scrutiny Officer (SR)", "scrutiny_officer", None, "SR"),
    ("auditor@flowguard.gov.in", "Audit Reviewer", "audit_reviewer", None, None),
]


async def seed_phase3_demo_data(db) -> int:
    created = 0
    regions = {r.code: r.id for r in (await db.execute(select(Region))).scalars().all()}
    for pid, name, region_code, state, city in PHASE3_INSTITUTIONS:
        if not (await db.execute(select(Institution).where(Institution.pid == pid))).scalar_one_or_none():
            db.add(Institution(pid=pid, name=name, institution_type="private",
                               region_id=regions[region_code], state=state, city=city))
            created += 1
    await db.flush()
    institutions = {i.pid: i.id for i in (await db.execute(select(Institution))).scalars().all()}
    for email, name, role, pid, region_code in PHASE3_USERS:
        if not (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
            db.add(User(email=email, hashed_password=hash_password("Demo@123"), full_name=name, role=role,
                        institution_id=institutions.get(pid) if pid else None,
                        region_id=regions.get(region_code) if region_code else None))
            created += 1
    await db.flush()
    return created


async def seed():
    async with async_session_factory() as db:
        existing = await db.execute(select(Role).limit(1))
        if existing.scalar_one_or_none():
            added = await seed_phase3_demo_data(db)
            await db.commit()
            print(f"Base data already present. Phase 3 demo rows added: {added}.")
            return

        # Roles
        for code, display in ROLES:
            db.add(Role(name=code, display_name=display))
        await db.flush()

        # Regions
        region_map = {}
        for code, name in REGIONS:
            r = Region(code=code, name=name)
            db.add(r)
            await db.flush()
            region_map[code] = r.id

        # Academic Year
        ay = AcademicYear(
            year_label="2024-25",
            start_date=date(2024, 8, 1),
            end_date=date(2025, 7, 31),
            is_current=True,
            public_notice_start=date(2024, 11, 1),
            public_notice_end=date(2025, 3, 31),
        )
        db.add(ay)
        ay2 = AcademicYear(
            year_label="2025-26",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
            is_current=False,
        )
        db.add(ay2)
        await db.flush()

        # Demo Institution
        inst = Institution(
            pid="AICTE-NR-2024-0001",
            name="Demo Institute of Technology",
            institution_type="private",
            region_id=region_map["NR"],
            state="Delhi",
            city="New Delhi",
            contact_email="demo@dit.ac.in",
        )
        db.add(inst)
        await db.flush()

        # Workflow Definitions
        wf_map = {}
        for wf_data in [WORKFLOW_FULL, WORKFLOW_SCRUTINY_ONLY, WORKFLOW_SELF_DISCLOSURE]:
            wf = WorkflowDefinition(
                name=wf_data["name"],
                route_type=wf_data["route_type"],
                stages=wf_data["stages"],
                transitions=wf_data["transitions"],
            )
            db.add(wf)
            await db.flush()
            wf_map[wf_data["route_type"]] = wf.id

        # Application Categories
        for cat in APPLICATION_CATEGORIES:
            code, name, proc_cat, sd, scr, evc, sac, route = cat
            db.add(ApplicationCategory(
                code=code,
                name=name,
                processing_category=proc_cat,
                requires_self_disclosure=sd,
                requires_scrutiny=scr,
                requires_evc=evc,
                sac_shc_applicable=sac,
                workflow_definition_id=wf_map[route],
            ))
        await db.flush()

        # Demo Users
        demo_users = [
            ("admin@flowguard.gov.in", "Admin User", "system_admin", None, None),
            ("institution@demo.ac.in", "Institution User", "institution_applicant", inst.id, region_map["NR"]),
            ("officer@flowguard.gov.in", "Regional Officer", "regional_officer", None, region_map["NR"]),
            ("scrutiny@flowguard.gov.in", "Scrutiny Officer", "scrutiny_officer", None, region_map["NR"]),
            ("evc@flowguard.gov.in", "EVC Coordinator", "evc_coordinator", None, region_map["NR"]),
            ("bureau@flowguard.gov.in", "Bureau Officer", "bureau_officer", None, None),
            ("authority@flowguard.gov.in", "Competent Authority", "competent_authority", None, None),
            ("compliance@flowguard.gov.in", "Compliance Officer", "compliance_officer", None, None),
            ("ruleadmin@flowguard.gov.in", "Rule Administrator", "rule_admin", None, None),
        ]
        for email, name, role, inst_id, reg_id in demo_users:
            db.add(User(
                email=email,
                hashed_password=hash_password("Demo@123"),
                full_name=name,
                role=role,
                institution_id=inst_id,
                region_id=reg_id,
            ))

        await db.flush()
        await seed_phase3_demo_data(db)
        await db.commit()
        print("Database seeded successfully.")
        print("Demo credentials: any user above with password 'Demo@123'")


if __name__ == "__main__":
    print(f"Migrations: {migrate()}.")
    asyncio.run(seed())

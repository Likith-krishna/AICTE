"""Single source of truth for system role codes and role groupings.

Role codes match the rows seeded into the ``roles`` table (see seed.py) and the
Role-Permission Matrix in spec §2.1. Groupings here drive data scoping
(app/core/scoping.py) and workflow role guards (app/services/workflow.py).
"""

INSTITUTION_APPLICANT = "institution_applicant"
INSTITUTION_SIGNATORY = "institution_signatory"
REGIONAL_OFFICER = "regional_officer"
SCRUTINY_OFFICER = "scrutiny_officer"
REGIONAL_COORDINATOR = "regional_coordinator"
BUREAU_OFFICER = "bureau_officer"
EVC_COORDINATOR = "evc_coordinator"
EVC_MEMBER = "evc_member"
SAC_SHC_MEMBER = "sac_shc_member"
COMPETENT_AUTHORITY = "competent_authority"
COMPLIANCE_OFFICER = "compliance_officer"
SYSTEM_ADMIN = "system_admin"
RULE_ADMIN = "rule_admin"
AUDIT_REVIEWER = "audit_reviewer"

ALL_ROLES: frozenset[str] = frozenset({
    INSTITUTION_APPLICANT, INSTITUTION_SIGNATORY, REGIONAL_OFFICER, SCRUTINY_OFFICER,
    REGIONAL_COORDINATOR, BUREAU_OFFICER, EVC_COORDINATOR, EVC_MEMBER, SAC_SHC_MEMBER,
    COMPETENT_AUTHORITY, COMPLIANCE_OFFICER, SYSTEM_ADMIN, RULE_ADMIN, AUDIT_REVIEWER,
})

# Users bound to exactly one institution; may only see that institution's data.
INSTITUTION_ROLES: frozenset[str] = frozenset({INSTITUTION_APPLICANT, INSTITUTION_SIGNATORY})

# Users bound to one region (spec §2.1: "cannot view outside assigned region").
# NOTE: EVC members are region-scoped for now; spec intends assignment-based
# scoping ("assigned cases"), which arrives with EVC assignments in Phase 4.
REGIONAL_ROLES: frozenset[str] = frozenset({
    REGIONAL_OFFICER, SCRUTINY_OFFICER, REGIONAL_COORDINATOR, EVC_COORDINATOR, EVC_MEMBER,
})

# Cross-region roles that may read application content.
NATIONAL_APPLICATION_ROLES: frozenset[str] = frozenset({
    BUREAU_OFFICER, COMPETENT_AUTHORITY, SAC_SHC_MEMBER, COMPLIANCE_OFFICER, AUDIT_REVIEWER,
})

# Spec §2.1: System Administrator "cannot access application content";
# Rule Administrator has no application responsibilities (least privilege).
NO_APPLICATION_CONTENT_ROLES: frozenset[str] = frozenset({SYSTEM_ADMIN, RULE_ADMIN})

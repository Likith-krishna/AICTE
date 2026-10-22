"""Category-aware application form schemas (single source for backend + frontend).

IMPORTANT — regulatory status of these fields
---------------------------------------------
These fields only *describe the request* (who to contact, what is being
changed). They are NOT the APH document/eligibility requirements for each
category: those live in APH Annexures that have not been verified into the
rule register (spec §13.1). No document list, eligibility criterion, fee or
deadline is encoded or enforced here. The schema is served to the frontend so
both sides validate against the same definition.
"""
from __future__ import annotations

import re
from typing import Any

FORM_SCHEMA_VERSION = 1

VERIFICATION_NOTE = (
    "Descriptive request fields only (prototype). Category-specific document and "
    "eligibility requirements from the APH Annexures are pending verification and "
    "are not collected or enforced by this form."
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = r"^[0-9+()\-\s]{7,20}$"

COMMON_FIELDS: list[dict[str, Any]] = [
    {"name": "contact_person_name", "label": "Contact person name", "type": "text",
     "required": True, "max_length": 200, "section": "Contact"},
    {"name": "contact_person_designation", "label": "Designation", "type": "text",
     "required": True, "max_length": 200, "section": "Contact"},
    {"name": "contact_email", "label": "Contact email", "type": "email",
     "required": True, "max_length": 320, "section": "Contact"},
    {"name": "contact_phone", "label": "Contact phone", "type": "tel",
     "required": True, "pattern": _PHONE_PATTERN, "section": "Contact",
     "help": "Digits, spaces, +, -, ( ) — 7 to 20 characters."},
    {"name": "request_summary", "label": "Summary of request", "type": "textarea",
     "required": True, "min_length": 20, "max_length": 4000, "section": "Request",
     "help": "Describe what the institution is requesting and why."},
]

_LEVELS = ["Diploma", "Post Diploma", "Under Graduate", "Post Graduate", "Doctoral", "Other"]

CATEGORY_FIELDS: dict[str, list[dict[str, Any]]] = {
    "INCREASE_INTAKE": [
        {"name": "programme_name", "label": "Programme", "type": "text", "required": True, "max_length": 200},
        {"name": "course_name", "label": "Course", "type": "text", "required": True, "max_length": 200},
        {"name": "level", "label": "Level", "type": "select", "required": True, "options": _LEVELS},
        {"name": "current_intake", "label": "Current approved intake", "type": "integer", "required": True, "min": 0, "max": 10000},
        {"name": "proposed_intake", "label": "Proposed intake", "type": "integer", "required": True, "min": 1, "max": 10000,
         "greater_than_field": "current_intake",
         "help": "An increase request must propose more seats than the current intake."},
    ],
    "NEW_PROGRAMME": [
        {"name": "programme_name", "label": "Programme", "type": "text", "required": True, "max_length": 200},
        {"name": "level", "label": "Level", "type": "select", "required": True, "options": _LEVELS},
        {"name": "proposed_intake", "label": "Proposed intake", "type": "integer", "required": True, "min": 1, "max": 10000},
    ],
    "NAME_CHANGE": [
        {"name": "current_name", "label": "Current name", "type": "text", "required": True, "max_length": 500},
        {"name": "proposed_name", "label": "Proposed name", "type": "text", "required": True, "max_length": 500,
         "different_from_field": "current_name"},
    ],
    "CHANGE_TRUST_NAME": [
        {"name": "current_name", "label": "Current Trust/Society/Company name", "type": "text", "required": True, "max_length": 500},
        {"name": "proposed_name", "label": "Proposed name", "type": "text", "required": True, "max_length": 500,
         "different_from_field": "current_name"},
    ],
    "COURSE_NAME_CHANGE": [
        {"name": "current_course_name", "label": "Current course name(s)", "type": "textarea", "required": True, "max_length": 2000},
        {"name": "proposed_change", "label": "Proposed change (rename / merger / reduction)", "type": "textarea",
         "required": True, "max_length": 2000},
    ],
    "CHANGE_OF_SITE": [
        {"name": "current_address", "label": "Current site address", "type": "textarea", "required": True, "max_length": 1000},
        {"name": "proposed_address", "label": "Proposed site address", "type": "textarea", "required": True, "max_length": 1000,
         "different_from_field": "current_address"},
    ],
    "CLOSURE_PROGRAMME": [
        {"name": "programmes_to_close", "label": "Programme(s)/course(s) proposed for closure", "type": "textarea",
         "required": True, "max_length": 2000},
    ],
}

DECLARATION_FIELD: dict[str, Any] = {
    "name": "declaration_accepted",
    "label": "I confirm that the information provided is accurate to the best of my knowledge.",
    "type": "checkbox", "required": True, "section": "Declaration",
}


def get_form_schema(category_code: str) -> dict[str, Any]:
    specific = [dict(f, section=f.get("section", "Category details")) for f in CATEGORY_FIELDS.get(category_code, [])]
    return {
        "category_code": category_code,
        "version": FORM_SCHEMA_VERSION,
        "verification_status": "PROTOTYPE_DESCRIPTIVE_FIELDS",
        "verification_note": VERIFICATION_NOTE,
        "has_category_fields": bool(specific),
        "fields": COMMON_FIELDS + specific + [DECLARATION_FIELD],
    }


def _is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def validate_form_data(category_code: str, data: dict[str, Any] | None, *, partial: bool) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate and normalise form data.

    ``partial=True`` (draft save) checks types/limits of supplied values only;
    ``partial=False`` (submission) also enforces required fields and cross-field
    checks. Returns ``(clean_data, errors)``.
    """
    schema = get_form_schema(category_code)
    fields = {f["name"]: f for f in schema["fields"]}
    data = data or {}
    errors: dict[str, str] = {}
    clean: dict[str, Any] = {}

    for key in data:
        if key not in fields:
            errors[key] = "Unknown field"

    for name, f in fields.items():
        v = data.get(name)
        if _is_blank(v) or (f["type"] == "checkbox" and v is False):
            if f["type"] == "checkbox" and v is False:
                clean[name] = False
            if not partial and f.get("required"):
                errors[name] = "This field is required" if f["type"] != "checkbox" else "You must accept the declaration"
            continue

        t = f["type"]
        if t in ("text", "textarea", "email", "tel", "select"):
            if not isinstance(v, str):
                errors[name] = "Must be text"
                continue
            v = v.strip()
            if "max_length" in f and len(v) > f["max_length"]:
                errors[name] = f"Must be at most {f['max_length']} characters"
            elif "min_length" in f and len(v) < f["min_length"] and not partial:
                errors[name] = f"Must be at least {f['min_length']} characters"
            elif t == "email" and not _EMAIL_RE.match(v):
                errors[name] = "Enter a valid email address"
            elif "pattern" in f and not re.match(f["pattern"], v):
                errors[name] = "Invalid format"
            elif t == "select" and v not in f["options"]:
                errors[name] = "Choose one of the listed options"
            clean[name] = v
        elif t == "integer":
            if isinstance(v, bool) or not isinstance(v, int):
                if isinstance(v, str) and v.strip().lstrip("-").isdigit():
                    v = int(v.strip())
                else:
                    errors[name] = "Must be a whole number"
                    continue
            if "min" in f and v < f["min"]:
                errors[name] = f"Must be at least {f['min']}"
            elif "max" in f and v > f["max"]:
                errors[name] = f"Must be at most {f['max']}"
            clean[name] = v
        elif t == "checkbox":
            if not isinstance(v, bool):
                errors[name] = "Must be true or false"
                continue
            clean[name] = v

    if not partial:
        for name, f in fields.items():
            if name in errors:
                continue
            other = f.get("greater_than_field")
            if other and isinstance(clean.get(name), int) and isinstance(clean.get(other), int):
                if clean[name] <= clean[other]:
                    errors[name] = f"Must be greater than {fields[other]['label'].lower()}"
            other = f.get("different_from_field")
            if other and isinstance(clean.get(name), str) and isinstance(clean.get(other), str):
                if clean[name].strip().lower() == clean[other].strip().lower():
                    errors[name] = f"Must differ from {fields[other]['label'].lower()}"

    return clean, errors

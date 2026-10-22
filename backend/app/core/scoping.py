"""Centralised, server-enforced data scoping.

Every list/detail/mutation endpoint that touches institution-owned data must
derive its visibility from these helpers rather than re-implementing role
checks. Safe default: anything not explicitly granted resolves to NO access.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import false

from app.core import roles as R

ScopeKind = Literal["institution", "region", "national", "none"]


@dataclass(frozen=True)
class AccessScope:
    kind: ScopeKind
    institution_id: uuid.UUID | None = None
    region_id: uuid.UUID | None = None

    @property
    def is_none(self) -> bool:
        return self.kind == "none"


NO_ACCESS = AccessScope("none")
NATIONAL = AccessScope("national")


def _bound_scope(user) -> AccessScope | None:
    """Scope for institution/regional users, or None if the role is not bound."""
    if user.role in R.INSTITUTION_ROLES:
        return AccessScope("institution", institution_id=user.institution_id) if user.institution_id else NO_ACCESS
    if user.role in R.REGIONAL_ROLES:
        return AccessScope("region", region_id=user.region_id) if user.region_id else NO_ACCESS
    return None


def institution_scope(user) -> AccessScope:
    """Visibility of institution master records."""
    bound = _bound_scope(user)
    if bound is not None:
        return bound
    if user.role in R.ALL_ROLES:
        return NATIONAL
    return NO_ACCESS


def application_scope(user, *, aggregate_only: bool = False) -> AccessScope:
    """Visibility of application records.

    ``aggregate_only`` is used for dashboard counts: administrators who may not
    read application *content* may still see national totals.
    """
    bound = _bound_scope(user)
    if bound is not None:
        return bound
    if user.role in R.NATIONAL_APPLICATION_ROLES:
        return NATIONAL
    if aggregate_only and user.role in R.NO_APPLICATION_CONTENT_ROLES:
        return NATIONAL
    return NO_ACCESS


def apply_scope(query, scope: AccessScope, *, institution_col, region_col):
    """Add the WHERE clause for ``scope`` to a SELECT."""
    if scope.kind == "none":
        return query.where(false())
    if scope.kind == "institution":
        return query.where(institution_col == scope.institution_id)
    if scope.kind == "region":
        return query.where(region_col == scope.region_id)
    return query


def scope_allows(scope: AccessScope, *, institution_id, region_id) -> bool:
    if scope.kind == "national":
        return True
    if scope.kind == "institution":
        return scope.institution_id is not None and scope.institution_id == institution_id
    if scope.kind == "region":
        return scope.region_id is not None and scope.region_id == region_id
    return False

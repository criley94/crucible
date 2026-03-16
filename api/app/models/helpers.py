"""Shared query helpers."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session


def resolve_id_or_slug(db: Session, model, id_or_slug: str, org_id: uuid.UUID):
    """Look up an entity by UUID or slug, scoped to org.

    Returns the entity or None.
    """
    # Try UUID first
    try:
        entity_id = uuid.UUID(id_or_slug)
        stmt = select(model).where(model.id == entity_id)
    except ValueError:
        # It's a slug
        stmt = select(model).where(model.slug == id_or_slug)

    # Scope to org
    if hasattr(model, "org_id"):
        stmt = stmt.where(model.org_id == org_id)

    return db.execute(stmt).scalar_one_or_none()

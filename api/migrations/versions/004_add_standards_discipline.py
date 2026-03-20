"""Add Standards Discipline as 9th evaluation dimension.

Creates the dimension for the hands-on-analytics org and adds
current_scores entries (null score, 0 reviews) for every agent in the org.

Revision ID: 004
Revises: 003
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

# Constants
DIMENSION_NAME = "Standards Discipline"
DIMENSION_DESC = (
    "Follows agreed standards without reminders, holds teammates to them, "
    "treats process commitments as non-negotiable"
)
SORT_ORDER = 9
ORG_SLUG = "hands-on-analytics"


def upgrade() -> None:
    conn = op.get_bind()

    # Get org id
    org_row = conn.execute(
        sa.text("SELECT id FROM organizations WHERE slug = :slug"),
        {"slug": ORG_SLUG},
    ).fetchone()
    if not org_row:
        raise RuntimeError(f"Organization '{ORG_SLUG}' not found. Cannot add dimension.")
    org_id = org_row[0]

    # Check if dimension already exists (idempotent)
    existing = conn.execute(
        sa.text(
            "SELECT id FROM evaluation_dimensions "
            "WHERE org_id = :org_id AND name = :name"
        ),
        {"org_id": org_id, "name": DIMENSION_NAME},
    ).fetchone()

    if existing:
        dim_id = existing[0]
    else:
        # Insert the new dimension
        result = conn.execute(
            sa.text(
                "INSERT INTO evaluation_dimensions (org_id, name, description, sort_order) "
                "VALUES (:org_id, :name, :desc, :sort_order) "
                "RETURNING id"
            ),
            {
                "org_id": org_id,
                "name": DIMENSION_NAME,
                "desc": DIMENSION_DESC,
                "sort_order": SORT_ORDER,
            },
        )
        dim_id = result.fetchone()[0]

    # Create agent_scores entries for all agents in this org that don't already
    # have a score for this dimension
    conn.execute(
        sa.text(
            "INSERT INTO agent_scores (agent_id, dimension_id, review_count) "
            "SELECT a.id, :dim_id, 0 "
            "FROM agents a "
            "WHERE a.org_id = :org_id "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM agent_scores s "
            "  WHERE s.agent_id = a.id AND s.dimension_id = :dim_id"
            ")"
        ),
        {"dim_id": dim_id, "org_id": org_id},
    )


def downgrade() -> None:
    conn = op.get_bind()

    org_row = conn.execute(
        sa.text("SELECT id FROM organizations WHERE slug = :slug"),
        {"slug": ORG_SLUG},
    ).fetchone()
    if not org_row:
        return
    org_id = org_row[0]

    dim_row = conn.execute(
        sa.text(
            "SELECT id FROM evaluation_dimensions "
            "WHERE org_id = :org_id AND name = :name"
        ),
        {"org_id": org_id, "name": DIMENSION_NAME},
    ).fetchone()
    if not dim_row:
        return
    dim_id = dim_row[0]

    # Remove agent_scores first (FK constraint)
    conn.execute(
        sa.text("DELETE FROM agent_scores WHERE dimension_id = :dim_id"),
        {"dim_id": dim_id},
    )

    # Remove the dimension
    conn.execute(
        sa.text("DELETE FROM evaluation_dimensions WHERE id = :dim_id"),
        {"dim_id": dim_id},
    )

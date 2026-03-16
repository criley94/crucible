"""Add Wave 2 experience columns and indexes.

Revision ID: 003
Revises: 002
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to experience_entries
    op.add_column(
        "experience_entries",
        sa.Column("title", sa.String(255), nullable=True),
    )
    op.add_column(
        "experience_entries",
        sa.Column("tags", ARRAY(sa.String(100)), server_default="{}", nullable=True),
    )
    op.add_column(
        "experience_entries",
        sa.Column("scope", sa.String(20), nullable=False, server_default="agent"),
    )
    op.add_column(
        "experience_entries",
        sa.Column("source_ref", sa.String(255), nullable=True),
    )

    # Indexes for common query patterns
    op.create_index("ix_experience_entries_agent_id", "experience_entries", ["agent_id"])
    op.create_index("ix_experience_entries_team_id", "experience_entries", ["team_id"])
    op.create_index("ix_experience_entries_project_ref_id", "experience_entries", ["project_ref_id"])
    op.create_index("ix_experience_entries_observation_type", "experience_entries", ["observation_type"])
    op.create_index("ix_experience_entries_scope", "experience_entries", ["scope"])
    op.create_index("ix_experience_entries_created_at", "experience_entries", ["created_at"])

    # Compound indexes for common retrieval patterns
    op.create_index("ix_experience_entries_org_agent", "experience_entries", ["org_id", "agent_id"])
    op.create_index("ix_experience_entries_org_team", "experience_entries", ["org_id", "team_id"])

    # HNSW vector index for semantic search
    op.execute(
        "CREATE INDEX ix_experience_entries_embedding ON experience_entries "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_experience_entries_embedding")
    op.drop_index("ix_experience_entries_org_team")
    op.drop_index("ix_experience_entries_org_agent")
    op.drop_index("ix_experience_entries_created_at")
    op.drop_index("ix_experience_entries_scope")
    op.drop_index("ix_experience_entries_observation_type")
    op.drop_index("ix_experience_entries_project_ref_id")
    op.drop_index("ix_experience_entries_team_id")
    op.drop_index("ix_experience_entries_agent_id")
    op.drop_column("experience_entries", "source_ref")
    op.drop_column("experience_entries", "scope")
    op.drop_column("experience_entries", "tags")
    op.drop_column("experience_entries", "title")

"""Widen agent_type column to 30 chars.

Revision ID: 002
Revises: 001
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("agents", "agent_type", type_=sa.String(30))


def downgrade() -> None:
    op.alter_column("agents", "agent_type", type_=sa.String(20))

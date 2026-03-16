"""Experience and review models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

VALID_OBSERVATION_TYPES = [
    "lesson",
    "pattern",
    "process_gap",
    "heuristic",
    "relationship_note",
    "decision",
    "observation",
    "recall",
]

VALID_SCOPES = ["agent", "team", "org"]


class ExperienceEntry(Base):
    __tablename__ = "experience_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id"), nullable=False
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    project_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_references.id"), nullable=True
    )
    observation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list | None] = mapped_column(ARRAY(String(100)), default=list)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="agent")
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # embedding column (vector(768)) managed via migration raw SQL
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "org_id": str(self.org_id),
            "agent_id": str(self.agent_id),
            "team_id": str(self.team_id) if self.team_id else None,
            "project_ref_id": str(self.project_ref_id) if self.project_ref_id else None,
            "observation_type": self.observation_type,
            "title": self.title,
            "body": self.body,
            "tags": self.tags or [],
            "scope": self.scope,
            "source_ref": self.source_ref,
            "created_at": self.created_at.isoformat(),
        }


class ReviewEntry(Base):
    __tablename__ = "review_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    subject_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id"), nullable=False
    )
    reviewer_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True
    )
    reviewer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    project_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_references.id"), nullable=True
    )
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    # narrative_embedding column (vector(768)) added in migration via raw SQL
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "org_id": str(self.org_id),
            "subject_agent_id": str(self.subject_agent_id),
            "reviewer_agent_id": str(self.reviewer_agent_id) if self.reviewer_agent_id else None,
            "reviewer_type": self.reviewer_type,
            "project_ref_id": str(self.project_ref_id) if self.project_ref_id else None,
            "scores": self.scores,
            "narrative": self.narrative,
            "created_at": self.created_at.isoformat(),
        }

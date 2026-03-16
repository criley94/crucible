"""Project reference models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectReference(Base):
    __tablename__ = "project_references"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_project_org_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    team_connections: Mapped[list["TeamProjectConnection"]] = relationship(
        back_populates="project"
    )

    def to_dict(self, include_teams=True):
        result = {
            "id": str(self.id),
            "org_id": str(self.org_id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_teams:
            result["connected_teams"] = [
                {
                    "id": str(tc.team.id),
                    "name": tc.team.name,
                    "slug": tc.team.slug,
                    "connected_at": tc.connected_at.isoformat(),
                }
                for tc in self.team_connections
                if tc.disconnected_at is None
            ]
        return result


class TeamProjectConnection(Base):
    __tablename__ = "team_project_connections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_references.id"), nullable=False
    )
    connected_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="project_connections")  # noqa: F821
    project: Mapped["ProjectReference"] = relationship(back_populates="team_connections")

    def to_dict(self):
        return {
            "id": str(self.id),
            "team_id": str(self.team_id),
            "project_id": str(self.project_id),
            "connected_at": self.connected_at.isoformat(),
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
        }

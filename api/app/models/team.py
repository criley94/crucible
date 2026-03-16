"""Team layer models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_team_org_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="teams")  # noqa: F821
    agents: Mapped[list["Agent"]] = relationship(back_populates="team")  # noqa: F821
    norms: Mapped[list["TeamNorm"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    project_connections: Mapped[list["TeamProjectConnection"]] = relationship(  # noqa: F821
        back_populates="team"
    )

    def to_dict(self, include_roster=True, include_norms=True, include_projects=True):
        result = {
            "id": str(self.id),
            "org_id": str(self.org_id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_roster:
            result["roster"] = [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "slug": a.slug,
                    "role": a.role,
                    "agent_type": a.agent_type,
                    "status": a.status,
                }
                for a in self.agents
                if a.status == "active"
            ]
        if include_norms:
            result["norms"] = [
                n.to_dict() for n in self.norms if n.status == "active"
            ]
        if include_projects:
            result["active_projects"] = [
                {
                    "id": str(pc.project.id),
                    "name": pc.project.name,
                    "slug": pc.project.slug,
                    "connected_at": pc.connected_at.isoformat(),
                }
                for pc in self.project_connections
                if pc.disconnected_at is None
            ]
        return result


class TeamNorm(Base):
    __tablename__ = "team_norms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    promoted_to_org: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    team: Mapped["Team"] = relationship(back_populates="norms")

    def to_dict(self):
        return {
            "id": str(self.id),
            "team_id": str(self.team_id),
            "title": self.title,
            "body": self.body,
            "status": self.status,
            "promoted_to_org": self.promoted_to_org,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

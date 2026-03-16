"""Agent layer models."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import String, Text, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_agent_org_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    persona: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[str] = mapped_column(Text, nullable=False)
    understanding: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationships: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    organization: Mapped["Organization"] = relationship(back_populates="agents")  # noqa: F821
    team: Mapped["Team | None"] = relationship(back_populates="agents")  # noqa: F821
    scores: Mapped[list["AgentScore"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )

    def to_dict(self, include_scores=True):
        result = {
            "id": str(self.id),
            "org_id": str(self.org_id),
            "team_id": str(self.team_id) if self.team_id else None,
            "name": self.name,
            "slug": self.slug,
            "agent_type": self.agent_type,
            "role": self.role,
            "persona": self.persona,
            "responsibilities": self.responsibilities,
            "understanding": self.understanding,
            "relationships": self.relationships,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_scores and self.scores:
            result["current_scores"] = [s.to_dict() for s in self.scores]
        elif include_scores:
            result["current_scores"] = []
        return result


class AgentScore(Base):
    __tablename__ = "agent_scores"
    __table_args__ = (
        UniqueConstraint(
            "agent_id", "dimension_id", name="uq_agent_dimension_score"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id"), nullable=False
    )
    dimension_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_dimensions.id"), nullable=False
    )
    current_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1), nullable=True
    )
    rolling_average: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1), nullable=True
    )
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    agent: Mapped["Agent"] = relationship(back_populates="scores")
    dimension: Mapped["EvaluationDimension"] = relationship()  # noqa: F821

    def to_dict(self):
        return {
            "dimension_id": str(self.dimension_id),
            "dimension_name": self.dimension.name if self.dimension else None,
            "current_score": float(self.current_score) if self.current_score else None,
            "rolling_average": float(self.rolling_average) if self.rolling_average else None,
            "review_count": self.review_count,
            "last_reviewed_at": self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
        }

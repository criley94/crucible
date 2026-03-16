"""Seed script: Migrate Nautilus team from markdown files into TeamForge database.

This is the real migration — reads actual identity files from disk and populates
the database with the Hands-On Analytics org, Nautilus team, all agents, evaluation
dimensions, project references, and an API key.

Run: python seed.py
"""

import os
import sys
import hashlib
import secrets

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent to path so we can import app modules
sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base
from app.models.organization import Organization, EvaluationDimension, OrgSuggestedNorm
from app.models.team import Team, TeamNorm
from app.models.agent import Agent, AgentScore
from app.models.project import ProjectReference, TeamProjectConnection
from app.models.api_key import ApiKey

# Paths
AI_TEAMS_ROOT = os.path.expanduser("~/workspace/ai-teams")
NAUTILUS_ROOT = os.path.join(AI_TEAMS_ROOT, "teams/nautilus")
ORG_ROOT = os.path.join(AI_TEAMS_ROOT, "org")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://teamforge:teamforge@localhost:5432/teamforge",
)


def read_file(path: str) -> str | None:
    """Read a file and return its contents, or None if not found."""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        print(f"  [warn] File not found: {path}")
        return None


def seed():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Check if already seeded
        existing_org = db.query(Organization).filter_by(slug="hands-on-analytics").first()
        if existing_org:
            print("Database already seeded. Skipping.")
            print(f"  Org: {existing_org.name} ({existing_org.slug})")
            # Still print the API key info
            key = db.query(ApiKey).filter_by(org_id=existing_org.id, is_active=True).first()
            if key:
                print(f"  API key prefix: {key.key_prefix}...")
            return

        print("=== Seeding TeamForge Database ===\n")

        # --- 1. Create Organization ---
        print("1. Creating organization: Hands-On Analytics")
        personal_statement = read_file(
            os.path.join(NAUTILUS_ROOT, "identity/personal_statement.md")
        )
        org = Organization(
            name="Hands-On Analytics",
            slug="hands-on-analytics",
            personal_statement=personal_statement,
        )
        db.add(org)
        db.flush()
        print(f"   Org ID: {org.id}")

        # --- 2. Create Evaluation Dimensions ---
        print("\n2. Creating evaluation dimensions")
        dimensions_data = [
            ("Honesty & Transparency", "Presents uncertainty honestly, shows reasoning, surfaces problems early", 1),
            ("Accountability", "Follows through on commitments, loops back proactively, owns mistakes", 2),
            ("Communication", "Direct, concise, respectful of time, delivers bad news straight", 3),
            ("Growth Orientation", "Learns from mistakes, gets better over time, balances correctness with momentum", 4),
            ("Constructive Challenge", "Pushes back when something is wrong, brings best thinking, executes once decided", 5),
            ("Risk Management", "Raises risks early, escalates when uncomfortable, prevents blindsides", 6),
            ("Grace & Support", "Gives teammates room to make mistakes, supports fixing and growing, lifts the team up", 7),
            ("Craftsmanship", "Cares about output quality, work is thorough and fit for purpose, takes pride in the result", 8),
        ]
        dimensions = {}
        for name, desc, order in dimensions_data:
            dim = EvaluationDimension(
                org_id=org.id, name=name, description=desc, sort_order=order
            )
            db.add(dim)
            db.flush()
            dimensions[name] = dim
            print(f"   {order}. {name}")

        # --- 3. Create Nautilus Team ---
        print("\n3. Creating team: Nautilus")
        team = Team(
            org_id=org.id,
            name="Nautilus",
            slug="nautilus",
            description="Primary development team for Hands-On Analytics",
        )
        db.add(team)
        db.flush()
        print(f"   Team ID: {team.id}")

        # --- 4. Create Agents ---
        print("\n4. Creating agents from markdown files")
        team_agents = [
            ("dante-tl", "Dante", "Tech Lead", "team_member"),
            ("maya-ra", "Maya", "Requirements Architect", "team_member"),
            ("lena-ux", "Lena", "UX Designer", "team_member"),
            ("nadia-pm", "Nadia", "Project Manager", "team_member"),
            ("chris-dev", "Chris", "Backend Developer", "team_member"),
            ("sofia-dev", "Sofia", "Frontend Developer", "team_member"),
            ("frank-qa", "Frank", "QA Engineer", "team_member"),
            ("quinn-historian", "Quinn", "Historian", "team_member"),
            ("james-po", "James", "Product Owner", "team_member"),
        ]

        for slug, name, role, agent_type in team_agents:
            agent_dir = os.path.join(NAUTILUS_ROOT, f"team/{slug}")
            persona = read_file(os.path.join(agent_dir, "persona.md")) or f"# {name}\n\n{role} on the Nautilus team."
            responsibilities = read_file(os.path.join(agent_dir, "responsibilities.md")) or f"# {name} Responsibilities\n\nSee team documentation."
            understanding = read_file(os.path.join(agent_dir, "understanding.md"))
            relationships = read_file(os.path.join(agent_dir, "relationships.md"))

            agent = Agent(
                org_id=org.id,
                team_id=team.id,
                name=name,
                slug=slug,
                agent_type=agent_type,
                role=role,
                persona=persona,
                responsibilities=responsibilities,
                understanding=understanding,
                relationships=relationships,
            )
            db.add(agent)
            db.flush()

            # Create empty score records for each dimension
            for dim_name, dim in dimensions.items():
                score = AgentScore(
                    agent_id=agent.id,
                    dimension_id=dim.id,
                )
                db.add(score)

            print(f"   {name} ({slug}) - {role}")

        # --- 5. Create Cloud Architect (Standalone Specialist) ---
        print("\n5. Creating standalone specialist: Cloud Architect")
        ca_file = os.path.join(ORG_ROOT, "agents/cloud-architect.md")
        ca_persona = read_file(ca_file) or "Cloud Architect for Hands-On Analytics."

        cloud_architect = Agent(
            org_id=org.id,
            team_id=None,
            name="Cloud Architect",
            slug="cloud-architect",
            agent_type="standalone_specialist",
            role="Cloud Architect",
            persona=ca_persona,
            responsibilities="Owns GCP infrastructure, cost management, networking, security posture.",
        )
        db.add(cloud_architect)
        db.flush()
        print(f"   Cloud Architect ({cloud_architect.id})")

        # --- 6. Create Project References ---
        print("\n6. Creating project references")
        projects = [
            ("Bookmark Manager", "bookmark-manager", "First team project — shakedown build"),
            ("TeamForge", "crucible", "Persistent agent team service — Phase 1"),
        ]
        project_refs = {}
        for pname, pslug, pdesc in projects:
            proj = ProjectReference(
                org_id=org.id, name=pname, slug=pslug, description=pdesc
            )
            db.add(proj)
            db.flush()
            project_refs[pslug] = proj
            print(f"   {pname} ({pslug})")

        # Connect Nautilus to Crucible (current project)
        conn = TeamProjectConnection(
            team_id=team.id, project_id=project_refs["crucible"].id
        )
        db.add(conn)
        print("   Connected Nautilus -> Crucible")

        # --- 7. Generate API Key ---
        print("\n7. Generating API key")
        raw_key = f"tf_{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]

        api_key = ApiKey(
            org_id=org.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name="Primary API key",
        )
        db.add(api_key)

        # Commit everything
        db.commit()

        print("\n=== Seed Complete ===")
        print(f"\n  Organization: {org.name}")
        print(f"  Team: Nautilus ({len(team_agents)} agents + 1 specialist)")
        print(f"  Evaluation dimensions: {len(dimensions_data)}")
        print(f"  Project references: {len(projects)}")
        print(f"\n  API Key (SAVE THIS — shown only once):")
        print(f"  {raw_key}")
        print(f"\n  Use this key in the X-API-Key header for all API requests.")

    except Exception as e:
        db.rollback()
        print(f"\nError during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

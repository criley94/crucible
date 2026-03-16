"""Team endpoints."""

from flask import Blueprint, request, jsonify, g

from app.database import SessionLocal
from app.middleware.auth import require_api_key
from app.models.team import Team
from app.models.agent import Agent
from app.models.project import ProjectReference, TeamProjectConnection
from app.models.helpers import resolve_id_or_slug

teams_bp = Blueprint("teams", __name__)


def paginate_query(query, page, per_page):
    """Apply pagination to a query."""
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),  # ceiling division
    }


@teams_bp.route("/api/v1/teams", methods=["POST"])
@require_api_key
def create_team():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("slug"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "name and slug are required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        existing = db.query(Team).filter_by(org_id=g.org_id, slug=data["slug"]).first()
        if existing:
            return jsonify({
                "error": {"code": "CONFLICT", "message": f"Team with slug '{data['slug']}' already exists.", "details": {}}
            }), 409

        team = Team(
            org_id=g.org_id,
            name=data["name"],
            slug=data["slug"],
            description=data.get("description"),
        )
        db.add(team)
        db.commit()
        db.refresh(team)
        return jsonify(team.to_dict()), 201
    finally:
        db.close()


@teams_bp.route("/api/v1/teams/<id_or_slug>", methods=["GET"])
@require_api_key
def get_team(id_or_slug):
    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, id_or_slug, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{id_or_slug}' not found.", "details": {}}
            }), 404
        return jsonify(team.to_dict())
    finally:
        db.close()


@teams_bp.route("/api/v1/teams/<id_or_slug>", methods=["PATCH"])
@require_api_key
def update_team(id_or_slug):
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, id_or_slug, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{id_or_slug}' not found.", "details": {}}
            }), 404

        if "name" in data:
            team.name = data["name"]
        if "description" in data:
            team.description = data["description"]

        db.commit()
        db.refresh(team)
        return jsonify(team.to_dict())
    finally:
        db.close()


@teams_bp.route("/api/v1/teams", methods=["GET"])
@require_api_key
def list_teams():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"

    db = SessionLocal()
    try:
        query = db.query(Team).filter(Team.org_id == g.org_id)
        if not include_inactive:
            query = query.filter(Team.status == "active")
        query = query.order_by(Team.name)

        items, pagination = paginate_query(query, page, per_page)
        return jsonify({
            "data": [t.to_dict(include_roster=False, include_norms=False, include_projects=False) for t in items],
            "pagination": pagination,
        })
    finally:
        db.close()


@teams_bp.route("/api/v1/teams/<id_or_slug>/deactivate", methods=["PATCH"])
@require_api_key
def deactivate_team(id_or_slug):
    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, id_or_slug, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{id_or_slug}' not found.", "details": {}}
            }), 404

        active_members = db.query(Agent).filter_by(team_id=team.id, status="active").count()
        if active_members > 0:
            return jsonify({
                "error": {
                    "code": "CONFLICT",
                    "message": f"Cannot deactivate team with {active_members} active member(s). Reassign or unassign agents first.",
                    "details": {},
                }
            }), 409

        team.status = "inactive"
        db.commit()
        db.refresh(team)
        return jsonify(team.to_dict())
    finally:
        db.close()


@teams_bp.route("/api/v1/teams/<id_or_slug>/activate", methods=["PATCH"])
@require_api_key
def activate_team(id_or_slug):
    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, id_or_slug, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{id_or_slug}' not found.", "details": {}}
            }), 404

        team.status = "active"
        db.commit()
        db.refresh(team)
        return jsonify(team.to_dict())
    finally:
        db.close()


# --- Team Composition ---


@teams_bp.route("/api/v1/teams/<team_ref>/members", methods=["POST"])
@require_api_key
def add_member(team_ref):
    data = request.get_json()
    if not data or not data.get("agent_id"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "agent_id is required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, team_ref, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{team_ref}' not found.", "details": {}}
            }), 404

        agent = resolve_id_or_slug(db, Agent, data["agent_id"], g.org_id)
        if not agent:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Agent '{data['agent_id']}' not found.", "details": {}}
            }), 404

        if agent.agent_type == "standalone_specialist":
            return jsonify({
                "error": {"code": "VALIDATION_ERROR", "message": "Standalone specialists cannot be added to teams.", "details": {}}
            }), 422

        if agent.team_id is not None and agent.team_id != team.id:
            return jsonify({
                "error": {"code": "CONFLICT", "message": "Agent is already on another team.", "details": {}}
            }), 409

        agent.team_id = team.id
        db.commit()
        db.refresh(team)
        return jsonify(team.to_dict())
    finally:
        db.close()


@teams_bp.route("/api/v1/teams/<team_ref>/members/<agent_ref>", methods=["DELETE"])
@require_api_key
def remove_member(team_ref, agent_ref):
    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, team_ref, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{team_ref}' not found.", "details": {}}
            }), 404

        agent = resolve_id_or_slug(db, Agent, agent_ref, g.org_id)
        if not agent or agent.team_id != team.id:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Agent '{agent_ref}' not on this team.", "details": {}}
            }), 404

        agent.team_id = None
        db.commit()
        return jsonify({"message": f"Agent '{agent.slug}' removed from team '{team.slug}'."})
    finally:
        db.close()


# --- Team-Project Connections ---


@teams_bp.route("/api/v1/teams/<team_ref>/projects", methods=["POST"])
@require_api_key
def connect_project(team_ref):
    data = request.get_json()
    if not data or not data.get("project_id"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "project_id is required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, team_ref, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{team_ref}' not found.", "details": {}}
            }), 404

        project = resolve_id_or_slug(db, ProjectReference, data["project_id"], g.org_id)
        if not project:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Project '{data['project_id']}' not found.", "details": {}}
            }), 404

        # Check for existing active connection
        existing = db.query(TeamProjectConnection).filter_by(
            team_id=team.id, project_id=project.id, disconnected_at=None
        ).first()
        if existing:
            return jsonify({
                "error": {"code": "CONFLICT", "message": "Team is already connected to this project.", "details": {}}
            }), 409

        conn = TeamProjectConnection(team_id=team.id, project_id=project.id)
        db.add(conn)
        db.commit()
        db.refresh(conn)
        return jsonify(conn.to_dict()), 201
    finally:
        db.close()


@teams_bp.route("/api/v1/teams/<team_ref>/projects/<project_ref>", methods=["DELETE"])
@require_api_key
def disconnect_project(team_ref, project_ref):
    from datetime import datetime, timezone

    db = SessionLocal()
    try:
        team = resolve_id_or_slug(db, Team, team_ref, g.org_id)
        if not team:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{team_ref}' not found.", "details": {}}
            }), 404

        project = resolve_id_or_slug(db, ProjectReference, project_ref, g.org_id)
        if not project:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Project '{project_ref}' not found.", "details": {}}
            }), 404

        conn = db.query(TeamProjectConnection).filter_by(
            team_id=team.id, project_id=project.id, disconnected_at=None
        ).first()
        if not conn:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": "No active connection found.", "details": {}}
            }), 404

        conn.disconnected_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(conn)
        return jsonify(conn.to_dict())
    finally:
        db.close()

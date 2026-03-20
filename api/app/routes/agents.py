"""Agent endpoints."""

from flask import Blueprint, request, jsonify, g

from app.database import SessionLocal
from app.middleware.auth import require_api_key
from app.models.agent import Agent
from app.models.helpers import resolve_id_or_slug
from app.utils.pagination import paginate_query

agents_bp = Blueprint("agents", __name__)


@agents_bp.route("/api/v1/agents", methods=["POST"])
@require_api_key
def create_agent():
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    required = ["name", "slug", "agent_type", "role"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"Missing required fields: {', '.join(missing)}",
                "details": {},
            }
        }), 422

    if data["agent_type"] not in ("team_member", "standalone_specialist"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "agent_type must be 'team_member' or 'standalone_specialist'.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        existing = db.query(Agent).filter_by(org_id=g.org_id, slug=data["slug"]).first()
        if existing:
            return jsonify({
                "error": {"code": "CONFLICT", "message": f"Agent with slug '{data['slug']}' already exists.", "details": {}}
            }), 409

        # Validate team_id if provided
        team_id = data.get("team_id")
        if team_id:
            from app.models.team import Team
            team = resolve_id_or_slug(db, Team, team_id, g.org_id)
            if not team:
                return jsonify({
                    "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Team '{team_id}' not found.", "details": {}}
                }), 404
            team_id = team.id
            if data["agent_type"] == "standalone_specialist":
                return jsonify({
                    "error": {"code": "VALIDATION_ERROR", "message": "Standalone specialists cannot be assigned to teams.", "details": {}}
                }), 422

        agent = Agent(
            org_id=g.org_id,
            team_id=team_id,
            name=data["name"],
            slug=data["slug"],
            agent_type=data["agent_type"],
            role=data["role"],
            persona=data.get("persona", ""),
            responsibilities=data.get("responsibilities", ""),
            understanding=data.get("understanding"),
            relationships=data.get("relationships"),
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return jsonify(agent.to_dict()), 201
    finally:
        db.close()


@agents_bp.route("/api/v1/agents/<id_or_slug>", methods=["GET"])
@require_api_key
def get_agent(id_or_slug):
    db = SessionLocal()
    try:
        agent = resolve_id_or_slug(db, Agent, id_or_slug, g.org_id)
        if not agent:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Agent '{id_or_slug}' not found.", "details": {}}
            }), 404
        return jsonify(agent.to_dict())
    finally:
        db.close()


@agents_bp.route("/api/v1/agents/<id_or_slug>", methods=["PATCH"])
@require_api_key
def update_agent(id_or_slug):
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        agent = resolve_id_or_slug(db, Agent, id_or_slug, g.org_id)
        if not agent:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Agent '{id_or_slug}' not found.", "details": {}}
            }), 404

        updatable = ["name", "persona", "responsibilities", "understanding", "relationships", "role"]
        for field in updatable:
            if field in data:
                setattr(agent, field, data[field])

        db.commit()
        db.refresh(agent)
        return jsonify(agent.to_dict())
    finally:
        db.close()


@agents_bp.route("/api/v1/agents", methods=["GET"])
@require_api_key
def list_agents():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    team_filter = request.args.get("team_id") or request.args.get("team_slug")
    unassigned = request.args.get("unassigned", "false").lower() == "true"
    agent_type = request.args.get("agent_type")

    db = SessionLocal()
    try:
        query = db.query(Agent).filter(Agent.org_id == g.org_id)

        if not include_inactive:
            query = query.filter(Agent.status == "active")
        if team_filter:
            from app.models.team import Team
            team = resolve_id_or_slug(db, Team, team_filter, g.org_id)
            if team:
                query = query.filter(Agent.team_id == team.id)
            else:
                return jsonify({"data": [], "pagination": {"total": 0, "page": 1, "per_page": per_page, "total_pages": 1}})
        if unassigned:
            query = query.filter(Agent.team_id == None)  # noqa: E711
        if agent_type:
            query = query.filter(Agent.agent_type == agent_type)

        query = query.order_by(Agent.name)
        items, pagination = paginate_query(query, page, per_page)

        return jsonify({
            "data": [a.to_dict(include_scores=False) for a in items],
            "pagination": pagination,
        })
    finally:
        db.close()


@agents_bp.route("/api/v1/agents/<id_or_slug>/deactivate", methods=["PATCH"])
@require_api_key
def deactivate_agent(id_or_slug):
    db = SessionLocal()
    try:
        agent = resolve_id_or_slug(db, Agent, id_or_slug, g.org_id)
        if not agent:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Agent '{id_or_slug}' not found.", "details": {}}
            }), 404

        agent.status = "inactive"
        db.commit()
        db.refresh(agent)
        return jsonify(agent.to_dict())
    finally:
        db.close()


@agents_bp.route("/api/v1/agents/<id_or_slug>/activate", methods=["PATCH"])
@require_api_key
def activate_agent(id_or_slug):
    db = SessionLocal()
    try:
        agent = resolve_id_or_slug(db, Agent, id_or_slug, g.org_id)
        if not agent:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Agent '{id_or_slug}' not found.", "details": {}}
            }), 404

        agent.status = "active"
        db.commit()
        db.refresh(agent)
        return jsonify(agent.to_dict())
    finally:
        db.close()

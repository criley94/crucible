"""Project reference endpoints."""

from flask import Blueprint, request, jsonify, g

from app.database import SessionLocal
from app.middleware.auth import require_api_key
from app.models.project import ProjectReference, TeamProjectConnection
from app.models.helpers import resolve_id_or_slug

projects_bp = Blueprint("projects", __name__)


def paginate_query(query, page, per_page):
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
    }


@projects_bp.route("/api/v1/projects", methods=["POST"])
@require_api_key
def create_project():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("slug"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "name and slug are required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        existing = db.query(ProjectReference).filter_by(org_id=g.org_id, slug=data["slug"]).first()
        if existing:
            return jsonify({
                "error": {"code": "CONFLICT", "message": f"Project with slug '{data['slug']}' already exists.", "details": {}}
            }), 409

        project = ProjectReference(
            org_id=g.org_id,
            name=data["name"],
            slug=data["slug"],
            description=data.get("description"),
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return jsonify(project.to_dict()), 201
    finally:
        db.close()


@projects_bp.route("/api/v1/projects/<id_or_slug>", methods=["GET"])
@require_api_key
def get_project(id_or_slug):
    db = SessionLocal()
    try:
        project = resolve_id_or_slug(db, ProjectReference, id_or_slug, g.org_id)
        if not project:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Project '{id_or_slug}' not found.", "details": {}}
            }), 404
        return jsonify(project.to_dict())
    finally:
        db.close()


@projects_bp.route("/api/v1/projects/<id_or_slug>", methods=["PATCH"])
@require_api_key
def update_project(id_or_slug):
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        project = resolve_id_or_slug(db, ProjectReference, id_or_slug, g.org_id)
        if not project:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Project '{id_or_slug}' not found.", "details": {}}
            }), 404

        if "name" in data:
            project.name = data["name"]
        if "description" in data:
            project.description = data["description"]

        db.commit()
        db.refresh(project)
        return jsonify(project.to_dict())
    finally:
        db.close()


@projects_bp.route("/api/v1/projects", methods=["GET"])
@require_api_key
def list_projects():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    db = SessionLocal()
    try:
        query = db.query(ProjectReference).filter(
            ProjectReference.org_id == g.org_id
        ).order_by(ProjectReference.name)

        items, pagination = paginate_query(query, page, per_page)
        return jsonify({
            "data": [p.to_dict(include_teams=False) for p in items],
            "pagination": pagination,
        })
    finally:
        db.close()


@projects_bp.route("/api/v1/projects/<id_or_slug>", methods=["DELETE"])
@require_api_key
def delete_project(id_or_slug):
    db = SessionLocal()
    try:
        project = resolve_id_or_slug(db, ProjectReference, id_or_slug, g.org_id)
        if not project:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Project '{id_or_slug}' not found.", "details": {}}
            }), 404

        active_connections = db.query(TeamProjectConnection).filter_by(
            project_id=project.id, disconnected_at=None
        ).count()
        if active_connections > 0:
            return jsonify({
                "error": {
                    "code": "CONFLICT",
                    "message": f"Cannot delete project with {active_connections} active team connection(s). Disconnect teams first.",
                    "details": {},
                }
            }), 409

        db.delete(project)
        db.commit()
        return "", 204
    finally:
        db.close()

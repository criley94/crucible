"""Organization endpoints."""

from flask import Blueprint, request, jsonify, g

from app.database import SessionLocal
from app.middleware.auth import require_api_key
from app.models.organization import Organization, EvaluationDimension
from app.models.helpers import resolve_id_or_slug

orgs_bp = Blueprint("orgs", __name__)


@orgs_bp.route("/api/v1/orgs", methods=["POST"])
@require_api_key
def create_org():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("slug"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "name and slug are required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        # Check duplicate slug
        existing = db.query(Organization).filter_by(slug=data["slug"]).first()
        if existing:
            return jsonify({
                "error": {"code": "CONFLICT", "message": f"Org with slug '{data['slug']}' already exists.", "details": {}}
            }), 409

        org = Organization(
            name=data["name"],
            slug=data["slug"],
            personal_statement=data.get("personal_statement"),
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return jsonify(org.to_dict()), 201
    finally:
        db.close()


@orgs_bp.route("/api/v1/orgs/<id_or_slug>", methods=["GET"])
@require_api_key
def get_org(id_or_slug):
    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, id_or_slug, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{id_or_slug}' not found.", "details": {}}
            }), 404
        return jsonify(org.to_dict())
    finally:
        db.close()


@orgs_bp.route("/api/v1/orgs/<id_or_slug>", methods=["PATCH"])
@require_api_key
def update_org(id_or_slug):
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, id_or_slug, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{id_or_slug}' not found.", "details": {}}
            }), 404

        if "name" in data:
            org.name = data["name"]
        if "personal_statement" in data:
            org.personal_statement = data["personal_statement"]

        db.commit()
        db.refresh(org)
        return jsonify(org.to_dict())
    finally:
        db.close()


# --- Evaluation Dimensions ---


def _reorder_dimensions_after_insert(db, org_id, target_sort_order):
    """Shift dimensions at target_sort_order and above up by 1."""
    dims = (
        db.query(EvaluationDimension)
        .filter_by(org_id=org_id)
        .filter(EvaluationDimension.sort_order >= target_sort_order)
        .order_by(EvaluationDimension.sort_order.desc())
        .all()
    )
    for d in dims:
        d.sort_order += 1


def _reorder_dimensions_contiguous(db, org_id, exclude_id=None):
    """Re-assign contiguous sort_order 1..N for all dimensions in the org.

    If exclude_id is given, that dimension is excluded from the contiguous
    re-numbering (it keeps its sort_order as the anchor, others fill around it).
    """
    dims = (
        db.query(EvaluationDimension)
        .filter_by(org_id=org_id)
        .order_by(EvaluationDimension.sort_order, EvaluationDimension.created_at)
        .all()
    )
    for i, d in enumerate(dims, start=1):
        if d.sort_order != i:
            d.sort_order = i


def _create_agent_scores_for_dimension(db, org_id, dimension_id):
    """Create agent_scores entries for all agents in the org for a new dimension."""
    from app.models.agent import Agent, AgentScore

    agents = db.query(Agent).filter_by(org_id=org_id).all()
    for agent in agents:
        existing = (
            db.query(AgentScore)
            .filter_by(agent_id=agent.id, dimension_id=dimension_id)
            .first()
        )
        if not existing:
            score = AgentScore(agent_id=agent.id, dimension_id=dimension_id)
            db.add(score)


@orgs_bp.route("/api/v1/orgs/<org_ref>/evaluation-dimensions", methods=["POST"])
@require_api_key
def create_evaluation_dimension(org_ref):
    data = request.get_json()
    if not data or not data.get("name") or not data.get("description"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "name and description are required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, org_ref, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{org_ref}' not found.", "details": {}}
            }), 404

        # Check duplicate name within org
        existing = db.query(EvaluationDimension).filter_by(
            org_id=org.id, name=data["name"]
        ).first()
        if existing:
            return jsonify({
                "error": {"code": "CONFLICT", "message": f"Dimension '{data['name']}' already exists.", "details": {}}
            }), 409

        # Determine sort_order
        if "sort_order" in data:
            target_order = data["sort_order"]
            # Shift existing dimensions at this position and above
            _reorder_dimensions_after_insert(db, org.id, target_order)
        else:
            # Default: place after the current last dimension
            from sqlalchemy import func
            max_order = (
                db.query(func.max(EvaluationDimension.sort_order))
                .filter_by(org_id=org.id)
                .scalar()
            ) or 0
            target_order = max_order + 1

        dim = EvaluationDimension(
            org_id=org.id,
            name=data["name"],
            description=data["description"],
            sort_order=target_order,
        )
        db.add(dim)
        db.flush()

        # Ensure contiguous sort_order
        _reorder_dimensions_contiguous(db, org.id)

        # Create agent_scores for all agents in the org
        _create_agent_scores_for_dimension(db, org.id, dim.id)

        db.commit()
        db.refresh(dim)
        return jsonify(dim.to_dict()), 201
    finally:
        db.close()


@orgs_bp.route("/api/v1/orgs/<org_ref>/evaluation-dimensions", methods=["GET"])
@require_api_key
def list_evaluation_dimensions(org_ref):
    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, org_ref, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{org_ref}' not found.", "details": {}}
            }), 404

        dims = db.query(EvaluationDimension).filter_by(org_id=org.id).order_by(
            EvaluationDimension.sort_order
        ).all()
        return jsonify([d.to_dict() for d in dims])
    finally:
        db.close()


@orgs_bp.route("/api/v1/orgs/<org_ref>/evaluation-dimensions/<dim_id>", methods=["PATCH"])
@require_api_key
def update_evaluation_dimension(org_ref, dim_id):
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, org_ref, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{org_ref}' not found.", "details": {}}
            }), 404

        dim = resolve_id_or_slug(db, EvaluationDimension, dim_id, g.org_id)
        if not dim or dim.org_id != org.id:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Dimension '{dim_id}' not found.", "details": {}}
            }), 404

        # Check duplicate name if name is being changed
        if "name" in data and data["name"] != dim.name:
            dup = db.query(EvaluationDimension).filter_by(
                org_id=org.id, name=data["name"]
            ).first()
            if dup:
                return jsonify({
                    "error": {"code": "CONFLICT", "message": f"Dimension '{data['name']}' already exists.", "details": {}}
                }), 409
            dim.name = data["name"]

        if "description" in data:
            dim.description = data["description"]

        if "sort_order" in data:
            new_order = data["sort_order"]
            old_order = dim.sort_order

            if new_order != old_order:
                # Move the dimension out of the way temporarily
                dim.sort_order = 0
                db.flush()

                if new_order < old_order:
                    # Moving up: shift dimensions in [new_order, old_order) up by 1
                    dims_to_shift = (
                        db.query(EvaluationDimension)
                        .filter_by(org_id=org.id)
                        .filter(
                            EvaluationDimension.sort_order >= new_order,
                            EvaluationDimension.sort_order < old_order,
                            EvaluationDimension.id != dim.id,
                        )
                        .order_by(EvaluationDimension.sort_order.desc())
                        .all()
                    )
                    for d in dims_to_shift:
                        d.sort_order += 1
                else:
                    # Moving down: shift dimensions in (old_order, new_order] down by 1
                    dims_to_shift = (
                        db.query(EvaluationDimension)
                        .filter_by(org_id=org.id)
                        .filter(
                            EvaluationDimension.sort_order > old_order,
                            EvaluationDimension.sort_order <= new_order,
                            EvaluationDimension.id != dim.id,
                        )
                        .order_by(EvaluationDimension.sort_order.asc())
                        .all()
                    )
                    for d in dims_to_shift:
                        d.sort_order -= 1

                dim.sort_order = new_order
                db.flush()

                # Final pass: ensure contiguous
                _reorder_dimensions_contiguous(db, org.id)

        db.commit()
        db.refresh(dim)
        return jsonify(dim.to_dict())
    finally:
        db.close()


# --- Legacy /dimensions routes (kept for backward compatibility) ---


@orgs_bp.route("/api/v1/orgs/<org_ref>/dimensions", methods=["POST"])
@require_api_key
def create_dimension(org_ref):
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "name is required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, org_ref, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{org_ref}' not found.", "details": {}}
            }), 404

        # Check duplicate name within org
        existing = db.query(EvaluationDimension).filter_by(
            org_id=org.id, name=data["name"]
        ).first()
        if existing:
            return jsonify({
                "error": {"code": "CONFLICT", "message": f"Dimension '{data['name']}' already exists.", "details": {}}
            }), 409

        dim = EvaluationDimension(
            org_id=org.id,
            name=data["name"],
            description=data.get("description"),
            sort_order=data.get("sort_order", 0),
        )
        db.add(dim)
        db.commit()
        db.refresh(dim)
        return jsonify(dim.to_dict()), 201
    finally:
        db.close()


@orgs_bp.route("/api/v1/orgs/<org_ref>/dimensions", methods=["GET"])
@require_api_key
def list_dimensions(org_ref):
    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, org_ref, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{org_ref}' not found.", "details": {}}
            }), 404

        dims = db.query(EvaluationDimension).filter_by(org_id=org.id).order_by(
            EvaluationDimension.sort_order
        ).all()
        return jsonify([d.to_dict() for d in dims])
    finally:
        db.close()


@orgs_bp.route("/api/v1/orgs/<org_ref>/dimensions/<dim_id>", methods=["PATCH"])
@require_api_key
def update_dimension(org_ref, dim_id):
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, org_ref, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{org_ref}' not found.", "details": {}}
            }), 404

        dim = resolve_id_or_slug(db, EvaluationDimension, dim_id, g.org_id)
        if not dim or dim.org_id != org.id:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Dimension '{dim_id}' not found.", "details": {}}
            }), 404

        if "name" in data:
            dim.name = data["name"]
        if "description" in data:
            dim.description = data["description"]
        if "sort_order" in data:
            dim.sort_order = data["sort_order"]

        db.commit()
        db.refresh(dim)
        return jsonify(dim.to_dict())
    finally:
        db.close()


@orgs_bp.route("/api/v1/orgs/<org_ref>/dimensions/<dim_id>", methods=["DELETE"])
@require_api_key
def delete_dimension(org_ref, dim_id):
    from app.models.agent import AgentScore

    db = SessionLocal()
    try:
        org = resolve_id_or_slug(db, Organization, org_ref, g.org_id)
        if not org:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Org '{org_ref}' not found.", "details": {}}
            }), 404

        dim = resolve_id_or_slug(db, EvaluationDimension, dim_id, g.org_id)
        if not dim or dim.org_id != org.id:
            return jsonify({
                "error": {"code": "RESOURCE_NOT_FOUND", "message": f"Dimension '{dim_id}' not found.", "details": {}}
            }), 404

        # Check for referencing scores
        score_count = db.query(AgentScore).filter_by(dimension_id=dim.id).count()
        if score_count > 0:
            return jsonify({
                "error": {
                    "code": "CONFLICT",
                    "message": f"Cannot delete dimension with {score_count} existing score(s). Rename instead.",
                    "details": {},
                }
            }), 409

        db.delete(dim)
        db.commit()
        return "", 204
    finally:
        db.close()

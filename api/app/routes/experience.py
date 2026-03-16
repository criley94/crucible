"""Experience capture and retrieval endpoints."""

import uuid
import logging

from flask import Blueprint, request, jsonify, g
from sqlalchemy import text

from app.database import SessionLocal
from app.middleware.auth import require_api_key
from app.models.experience import ExperienceEntry, VALID_OBSERVATION_TYPES, VALID_SCOPES
from app.models.agent import Agent
from app.services.embedding import embed_text, embed_texts

logger = logging.getLogger(__name__)

experience_bp = Blueprint("experience", __name__)


def _validate_entry(data, db):
    """Validate a single experience entry payload. Returns (errors, agent) tuple."""
    errors = []

    if not data.get("agent_id"):
        errors.append("agent_id is required")
    if not data.get("observation_type"):
        errors.append("observation_type is required")
    if not data.get("body") or not data["body"].strip():
        errors.append("body is required and must be non-empty")

    if data.get("observation_type") and data["observation_type"] not in VALID_OBSERVATION_TYPES:
        errors.append(
            f"observation_type must be one of: {', '.join(VALID_OBSERVATION_TYPES)}"
        )

    if data.get("scope") and data["scope"] not in VALID_SCOPES:
        errors.append(f"scope must be one of: {', '.join(VALID_SCOPES)}")

    agent = None
    if data.get("agent_id") and not errors:
        try:
            agent_uuid = uuid.UUID(data["agent_id"])
        except ValueError:
            errors.append("agent_id must be a valid UUID")
            return errors, None

        agent = db.query(Agent).filter_by(
            id=agent_uuid, org_id=g.org_id
        ).first()
        if not agent:
            errors.append(f"Agent {data['agent_id']} not found in this org")
        elif agent.status != "active":
            errors.append(f"Agent {data['agent_id']} is not active")

    return errors, agent


def _create_entry(data, db, embedding=None):
    """Create an ExperienceEntry from validated data."""
    entry = ExperienceEntry(
        org_id=g.org_id,
        agent_id=uuid.UUID(data["agent_id"]),
        team_id=uuid.UUID(data["team_id"]) if data.get("team_id") else None,
        project_ref_id=uuid.UUID(data["project_ref_id"]) if data.get("project_ref_id") else None,
        observation_type=data["observation_type"],
        title=data.get("title"),
        body=data["body"],
        tags=data.get("tags", []),
        scope=data.get("scope", "agent"),
        source_ref=data.get("source_ref"),
    )
    db.add(entry)
    db.flush()

    # Set embedding via raw SQL (pgvector column not in ORM)
    if embedding:
        db.execute(
            text("UPDATE experience_entries SET embedding = :emb WHERE id = :id"),
            {"emb": str(embedding), "id": str(entry.id)},
        )

    return entry


@experience_bp.route("/api/v1/experience", methods=["POST"])
@require_api_key
def create_experience():
    """Create a single experience entry."""
    data = request.get_json()
    if not data:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body required.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        errors, agent = _validate_entry(data, db)
        if errors:
            return jsonify({
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "; ".join(errors),
                    "details": {},
                }
            }), 422

        # Generate embedding synchronously
        embedding = embed_text(data["body"])

        entry = _create_entry(data, db, embedding)
        db.commit()
        db.refresh(entry)

        result = entry.to_dict()
        if not embedding:
            result["_warning"] = "Embedding generation failed; entry will not appear in vector search"

        return jsonify(result), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating experience entry: {e}")
        return jsonify({
            "error": {"code": "INTERNAL_ERROR", "message": "Failed to create experience entry.", "details": {}}
        }), 500
    finally:
        db.close()


@experience_bp.route("/api/v1/experience/batch", methods=["POST"])
@require_api_key
def create_experience_batch():
    """Create multiple experience entries atomically."""
    data = request.get_json()
    if not data or not data.get("entries"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body with 'entries' array required.", "details": {}}
        }), 422

    entries_data = data["entries"]
    if len(entries_data) > 50:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Maximum 50 entries per batch.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        # Validate all entries first (atomic — reject all if any fail)
        all_errors = []
        for i, entry_data in enumerate(entries_data):
            errors, _ = _validate_entry(entry_data, db)
            if errors:
                all_errors.append({"index": i, "errors": errors})

        if all_errors:
            return jsonify({
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Validation failed for {len(all_errors)} entries.",
                    "details": {"entries": all_errors},
                }
            }), 422

        # Generate embeddings in batch
        bodies = [e["body"] for e in entries_data]
        embeddings = embed_texts(bodies)

        # Create all entries
        created = []
        for entry_data, embedding in zip(entries_data, embeddings):
            entry = _create_entry(entry_data, db, embedding)
            created.append(entry)

        db.commit()
        for entry in created:
            db.refresh(entry)

        return jsonify({"entries": [e.to_dict() for e in created]}), 201
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating experience batch: {e}")
        return jsonify({
            "error": {"code": "INTERNAL_ERROR", "message": "Failed to create experience batch.", "details": {}}
        }), 500
    finally:
        db.close()


@experience_bp.route("/api/v1/experience/search", methods=["POST"])
@require_api_key
def search_experience():
    """Semantic search for experience entries with privacy boundaries."""
    data = request.get_json()
    if not data or not data.get("query"):
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Request body with 'query' field required.", "details": {}}
        }), 422

    query_text = data["query"]
    filters = data.get("filters", {})
    limit = min(data.get("limit", 10), 50)
    min_similarity = data.get("min_similarity", 0.0)

    # The caller MUST provide agent_id so we can enforce privacy boundaries
    caller_agent_id = filters.get("agent_id")
    caller_team_id = filters.get("team_id")

    if not caller_agent_id:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "filters.agent_id is required for search (privacy boundary enforcement).",
                "details": {},
            }
        }), 422

    # Embed the search query
    query_embedding = embed_text(query_text)
    if not query_embedding:
        return jsonify({
            "error": {"code": "EMBEDDING_ERROR", "message": "Failed to generate embedding for search query.", "details": {}}
        }), 503

    db = SessionLocal()
    try:
        # Build the search query with privacy boundaries (AD17)
        # An agent sees: own entries + team shared + org shared
        # NEVER another agent's personal entries
        params = {
            "org_id": str(g.org_id),
            "caller_agent_id": caller_agent_id,
            "query_embedding": str(query_embedding),
            "limit": limit,
            "min_similarity": min_similarity,
        }

        privacy_clause = """
            (e.agent_id = :caller_agent_id
             OR (e.scope = 'org'))
        """
        if caller_team_id:
            privacy_clause = """
                (e.agent_id = :caller_agent_id
                 OR (e.scope = 'team' AND e.team_id = :caller_team_id)
                 OR (e.scope = 'org'))
            """
            params["caller_team_id"] = caller_team_id

        # Additional optional filters
        extra_filters = ""
        if filters.get("observation_types"):
            extra_filters += " AND e.observation_type = ANY(:obs_types)"
            params["obs_types"] = filters["observation_types"]
        if filters.get("project_ref_id"):
            extra_filters += " AND e.project_ref_id = :filter_project"
            params["filter_project"] = filters["project_ref_id"]
        if filters.get("scope"):
            extra_filters += " AND e.scope = :filter_scope"
            params["filter_scope"] = filters["scope"]
        if filters.get("tags"):
            extra_filters += " AND e.tags && :filter_tags"
            params["filter_tags"] = filters["tags"]
        if filters.get("created_after"):
            extra_filters += " AND e.created_at >= :created_after"
            params["created_after"] = filters["created_after"]
        if filters.get("created_before"):
            extra_filters += " AND e.created_at <= :created_before"
            params["created_before"] = filters["created_before"]

        sql = f"""
            SELECT
                e.id, e.agent_id, a.name as agent_name, e.team_id,
                e.project_ref_id, e.observation_type, e.title, e.body,
                e.tags, e.scope, e.source_ref, e.created_at,
                1 - (e.embedding <=> CAST(:query_embedding AS vector)) as similarity
            FROM experience_entries e
            JOIN agents a ON e.agent_id = a.id
            WHERE e.org_id = :org_id
              AND e.embedding IS NOT NULL
              AND ({privacy_clause})
              {extra_filters}
            ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """

        rows = db.execute(text(sql), params).fetchall()

        # Count total searchable entries
        count_sql = f"""
            SELECT COUNT(*) FROM experience_entries e
            WHERE e.org_id = :org_id
              AND e.embedding IS NOT NULL
              AND ({privacy_clause})
              {extra_filters}
        """
        total = db.execute(text(count_sql), params).scalar()

        results = []
        for row in rows:
            sim = float(row.similarity) if row.similarity else 0.0
            if sim < min_similarity:
                continue
            results.append({
                "id": str(row.id),
                "agent_id": str(row.agent_id),
                "agent_name": row.agent_name,
                "team_id": str(row.team_id) if row.team_id else None,
                "project_ref_id": str(row.project_ref_id) if row.project_ref_id else None,
                "observation_type": row.observation_type,
                "title": row.title,
                "body": row.body,
                "tags": row.tags or [],
                "scope": row.scope,
                "source_ref": row.source_ref,
                "created_at": row.created_at.isoformat(),
                "similarity": round(sim, 4),
            })

        return jsonify({
            "results": results,
            "total_searched": total,
            "query": query_text,
        }), 200
    except Exception as e:
        logger.error(f"Error searching experience: {e}")
        return jsonify({
            "error": {"code": "INTERNAL_ERROR", "message": "Search failed.", "details": {}}
        }), 500
    finally:
        db.close()


@experience_bp.route("/api/v1/experience/<experience_id>", methods=["GET"])
@require_api_key
def get_experience(experience_id):
    """Retrieve a single experience entry by ID."""
    try:
        exp_uuid = uuid.UUID(experience_id)
    except ValueError:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Invalid experience ID format.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        entry = db.query(ExperienceEntry).filter_by(
            id=exp_uuid, org_id=g.org_id
        ).first()
        if not entry:
            return jsonify({
                "error": {"code": "NOT_FOUND", "message": "Experience entry not found.", "details": {}}
            }), 404
        return jsonify(entry.to_dict()), 200
    finally:
        db.close()


@experience_bp.route("/api/v1/agents/<agent_id>/experience", methods=["GET"])
@require_api_key
def list_agent_experience(agent_id):
    """List experience entries authored by a specific agent."""
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        return jsonify({
            "error": {"code": "VALIDATION_ERROR", "message": "Invalid agent ID format.", "details": {}}
        }), 422

    db = SessionLocal()
    try:
        # Verify agent exists in this org
        agent = db.query(Agent).filter_by(id=agent_uuid, org_id=g.org_id).first()
        if not agent:
            return jsonify({
                "error": {"code": "NOT_FOUND", "message": "Agent not found.", "details": {}}
            }), 404

        query = db.query(ExperienceEntry).filter_by(
            agent_id=agent_uuid, org_id=g.org_id
        )

        # Optional filters
        obs_type = request.args.get("observation_type")
        if obs_type:
            query = query.filter_by(observation_type=obs_type)

        scope = request.args.get("scope")
        if scope:
            query = query.filter_by(scope=scope)

        project_ref_id = request.args.get("project_ref_id")
        if project_ref_id:
            query = query.filter_by(project_ref_id=uuid.UUID(project_ref_id))

        # Pagination
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = int(request.args.get("offset", 0))

        total = query.count()
        entries = query.order_by(ExperienceEntry.created_at.desc()).offset(offset).limit(limit).all()

        return jsonify({
            "entries": [e.to_dict() for e in entries],
            "total": total,
            "limit": limit,
            "offset": offset,
        }), 200
    finally:
        db.close()

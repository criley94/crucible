"""Health check endpoint."""

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.database import SessionLocal

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/v1/health", methods=["GET"])
def health_check():
    """Health check — no auth required."""
    db_status = "connected"
    db_error = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = "disconnected"
        db_error = str(e)

    from datetime import datetime, timezone

    result = {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if db_error:
        result["error"] = db_error
    return jsonify(result)

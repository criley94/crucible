"""API key authentication middleware."""

import hashlib
from datetime import datetime, timezone
from functools import wraps

from flask import request, g, jsonify
from sqlalchemy import select

from app.database import SessionLocal
from app.models.api_key import ApiKey


def require_api_key(f):
    """Decorator that enforces API key authentication.

    Extracts X-API-Key header, validates it, and sets g.org_id.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "X-API-Key header is required.",
                    "details": {},
                }
            }), 401

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        db = SessionLocal()
        try:
            stmt = select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,  # noqa: E712
            )
            key_record = db.execute(stmt).scalar_one_or_none()

            if not key_record:
                return jsonify({
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "Invalid or revoked API key.",
                        "details": {},
                    }
                }), 401

            # Set org context
            g.org_id = key_record.org_id
            g.api_key_id = key_record.id

            # Update last_used_at
            key_record.last_used_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

        return f(*args, **kwargs)

    return decorated

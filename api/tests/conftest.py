"""Test fixtures — real PostgreSQL, no mocking."""

import os
import hashlib
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Must set before importing app modules
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://teamforge:teamforge@localhost:5432/teamforge_test",
)
os.environ["DATABASE_URL"] = TEST_DB_URL

from app.create_app import create_app
from app.database import Base, init_engine, SessionLocal
from app.models import *  # noqa: F401,F403


@pytest.fixture(scope="session")
def db_engine():
    """Create test database and return engine."""
    # Connect to default db to create test db
    admin_url = "postgresql://teamforge:teamforge@localhost:5432/teamforge"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        # Drop and recreate test database
        conn.execute(text("DROP DATABASE IF EXISTS teamforge_test"))
        conn.execute(text("CREATE DATABASE teamforge_test"))
    admin_engine.dispose()

    # Create engine for test database
    engine = init_engine(TEST_DB_URL)

    # Enable pgvector and create tables
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(engine)

    # Add vector columns (not handled by SQLAlchemy metadata)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE experience_entries ADD COLUMN IF NOT EXISTS embedding vector(768)"))
        conn.execute(text("ALTER TABLE review_entries ADD COLUMN IF NOT EXISTS narrative_embedding vector(768)"))
        conn.commit()

    yield engine

    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(db_engine):
    """Truncate all tables between tests."""
    session = sessionmaker(bind=db_engine)()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
    yield


@pytest.fixture
def app(db_engine):
    """Create Flask test app."""
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def seed_org():
    """Create an org and return (org, api_key_raw)."""
    from app.models.organization import Organization
    from app.models.api_key import ApiKey
    import secrets

    db = SessionLocal()
    try:
        org = Organization(name="Test Org", slug="test-org")
        db.add(org)
        db.flush()

        raw_key = f"tf_{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = ApiKey(
            org_id=org.id,
            key_hash=key_hash,
            key_prefix=raw_key[:8],
            name="Test key",
        )
        db.add(api_key)
        db.commit()
        db.refresh(org)
        return org, raw_key
    finally:
        db.close()


@pytest.fixture
def auth_header(seed_org):
    """Return auth headers dict."""
    _, raw_key = seed_org
    return {"X-API-Key": raw_key, "Content-Type": "application/json"}


@pytest.fixture
def org(seed_org):
    """Return just the org."""
    return seed_org[0]

"""Application configuration."""

import os


class Config:
    """Base configuration."""

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://teamforge:teamforge@localhost:5432/teamforge",
    )
    SQLALCHEMY_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
    SQLALCHEMY_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "30"))


class TestConfig(Config):
    """Test configuration."""

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://teamforge:teamforge@localhost:5432/teamforge_test",
    )
    TESTING = True

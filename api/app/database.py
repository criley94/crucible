"""Database engine and session management."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import Config


def _create_engine():
    """Create the SQLAlchemy engine from config."""
    uri = Config.SQLALCHEMY_DATABASE_URI
    return create_engine(
        uri,
        pool_size=Config.SQLALCHEMY_POOL_SIZE,
        max_overflow=Config.SQLALCHEMY_MAX_OVERFLOW,
        pool_timeout=Config.SQLALCHEMY_POOL_TIMEOUT,
        pool_pre_ping=True,
    )


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Yield a database session, closing it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_engine(database_url: str, **kwargs):
    """Reinitialize the engine with a new URL. Used for testing."""
    global engine, SessionLocal
    engine = create_engine(database_url, pool_pre_ping=True, **kwargs)
    SessionLocal = sessionmaker(bind=engine)
    return engine

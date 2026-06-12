from __future__ import annotations

from typing import Any, Generator, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings, get_config
from app.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide a synchronous database session (psycopg2-based)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_redis() -> Any:
    """Get a synchronous Redis client."""
    import redis
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)

"""
Database connection and session management - PostgreSQL only.

Provides:
- PostgreSQL engine for all data
- Session management
- Database initialization
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URLs
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/quant_db"
)

# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

# ---------------------------------------------------------------------------
# Session makers
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Session context managers
# ---------------------------------------------------------------------------

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Unlike ``get_session`` (a ``@contextmanager``), this is a plain generator
    suitable for ``Depends(...)`` so FastAPI injects the ``Session`` itself
    rather than the context-manager object.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Initialize PostgreSQL: create all tables."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create hypertables for timeseries data
    with engine.connect() as conn:
        # Check if TimescaleDB extension is installed
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                )
            """))
            timescaledb_installed = result.scalar()
            
            if not timescaledb_installed:
                logger.warning("[DB] TimescaleDB extension not installed. Hypertables will not be created.")
            else:
                # Check if ohlcv_1h hypertable exists
                result = conn.execute(text("""
                    SELECT hypertable_name 
                    FROM timescaledb_information.hypertables 
                    WHERE hypertable_name = 'ohlcv_1h'
                """))
                
                if result.fetchone() is None:
                    conn.execute(text("""
                        SELECT create_hypertable('ohlcv_1h', 'ts', if_not_exists => TRUE)
                    """))
                    conn.commit()
                    logger.info("[DB] Created hypertable: ohlcv_1h")
                
                # Check if ohlcv_1d hypertable exists
                result = conn.execute(text("""
                    SELECT hypertable_name 
                    FROM timescaledb_information.hypertables 
                    WHERE hypertable_name = 'ohlcv_1d'
                """))
                
                if result.fetchone() is None:
                    conn.execute(text("""
                        SELECT create_hypertable('ohlcv_1d', 'ts', if_not_exists => TRUE)
                    """))
                    conn.commit()
                    logger.info("[DB] Created hypertable: ohlcv_1d")
                
                # Check if factor_values hypertable exists
                result = conn.execute(text("""
                    SELECT hypertable_name 
                    FROM timescaledb_information.hypertables 
                    WHERE hypertable_name = 'factor_values'
                """))
                
                if result.fetchone() is None:
                    conn.execute(text("""
                        SELECT create_hypertable('factor_values', 'ts', if_not_exists => TRUE)
                    """))
                    conn.commit()
                    logger.info("[DB] Created hypertable: factor_values")
        except Exception as e:
            logger.warning(f"[DB] TimescaleDB hypertable creation failed: {e}")
    
    # Initialize the separate SQLite evolution store (its own Base/engine in
    # quant_engine.core.models.evolution). Without this, tables such as
    # evolution_factors / factor_live_stats never exist and routes 500 with
    # "no such table".
    try:
        from quant_engine.core.models.evolution import (
            Base as EvolutionBase,
            sqlite_engine,
        )
        EvolutionBase.metadata.create_all(bind=sqlite_engine)
        logger.info("[DB] SQLite evolution tables initialized")
    except Exception as e:
        logger.warning(f"[DB] SQLite evolution table init failed: {e}")
    
    logger.info("[DB] All tables initialized")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def check_health() -> bool:
    """Check database connection health."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"[DB] Health check failed: {e}")
        return False


def get_pool_status() -> Dict[str, Any]:
    """Get database connection pool status."""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": engine.pool._max_overflow,
        "pool_timeout": engine.pool._timeout,
    }

"""Redis client for caching and pub/sub."""

import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def check_redis_health() -> bool:
    """Check Redis connection health."""
    try:
        client = get_redis_client()
        return client.ping()
    except Exception as e:
        logger.warning(f"[Redis] Health check failed: {e}")
        return False

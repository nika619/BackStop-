import os
import threading
from typing import Optional

# Global fallback in-memory lock set for offline / test environments
_LOCAL_LOCK_SET: set[str] = set()
_LOCAL_LOCK_MUTEX = threading.Lock()

try:
    import redis

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Connection pool with short socket timeout to fail fast if Redis server is down
    redis_client: Optional[redis.Redis] = redis.Redis.from_url(
        REDIS_URL, socket_timeout=0.5, socket_connect_timeout=0.5
    )
except Exception:
    redis_client = None


def acquire_idempotency_lock(
    merchant_id: str,
    payment_id: str,
    attempt_no: int,
    ttl_seconds: int = 60,
) -> bool:
    """
    Acquires an idempotency lock for cross-pod Kubernetes safety.
    Key format: lock:idempotency:{mid}:{payment_id}:{attempt_no}
    Uses Redis SETNX with TTL. If Redis is unavailable, falls back to thread-safe memory lock.

    Returns True if lock acquired successfully (first execution).
    Returns False if lock is already held (duplicate attempt).
    """
    lock_key = f"lock:idempotency:{merchant_id}:{payment_id}:{attempt_no}"

    if redis_client:
        try:
            # nx=True sets key only if it does not exist (SETNX)
            acquired = redis_client.set(lock_key, "LOCKED", ex=ttl_seconds, nx=True)
            if acquired:
                return True
            else:
                return False
        except Exception:
            pass  # Fall through to in-memory fallback on Redis network error

    # Thread-safe in-memory fallback
    with _LOCAL_LOCK_MUTEX:
        if lock_key in _LOCAL_LOCK_SET:
            return False
        _LOCAL_LOCK_SET.add(lock_key)
        return True


def release_idempotency_lock(merchant_id: str, payment_id: str, attempt_no: int):
    """
    Releases an idempotency lock (optional cleanup).
    """
    lock_key = f"lock:idempotency:{merchant_id}:{payment_id}:{attempt_no}"
    if redis_client:
        try:
            redis_client.delete(lock_key)
        except Exception:
            pass
    with _LOCAL_LOCK_MUTEX:
        _LOCAL_LOCK_SET.discard(lock_key)

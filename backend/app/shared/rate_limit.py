"""Process-local rate limiter using `slowapi`.

We keep a single shared `Limiter` so all routers share state. In multi-worker
deployments the limits are per-worker (in-memory storage). If we need a global
view across workers, switch the `storage_uri` to Redis via env `NONGTRI_RATE_LIMIT_STORAGE`.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


# Default budgets — chosen to absorb mobile retries (3G dropped connections)
# while still cutting off spammers / cost-burn attacks.
DEFAULT_CHAT_LIMIT = os.getenv("NONGTRI_RATE_LIMIT_CHAT", "60/minute")
DEFAULT_IMAGE_LIMIT = os.getenv("NONGTRI_RATE_LIMIT_IMAGE", "10/minute")
DEFAULT_ADMIN_LIMIT = os.getenv("NONGTRI_RATE_LIMIT_ADMIN", "30/minute")


def _build_limiter() -> Limiter:
    storage_uri = os.getenv("NONGTRI_RATE_LIMIT_STORAGE", "memory://")
    return Limiter(key_func=get_remote_address, storage_uri=storage_uri)


limiter = _build_limiter()

__all__ = [
    "limiter",
    "DEFAULT_CHAT_LIMIT",
    "DEFAULT_IMAGE_LIMIT",
    "DEFAULT_ADMIN_LIMIT",
    "RateLimitExceeded",
]

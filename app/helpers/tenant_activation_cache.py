"""Short-lived cache for tenant suspension / activation checks in middleware."""

from __future__ import annotations

import os
import time
from typing import Optional, Tuple

# tenant_id -> (timestamp, is_suspended, is_activated)
_CACHE: dict[int, Tuple[float, bool, bool]] = {}
_CACHE_TTL_SECONDS = int(os.getenv("TENANT_ACTIVATION_CACHE_TTL", "120"))


def get_tenant_access_status(tenant_id: int) -> Optional[Tuple[bool, bool]]:
    """Return (is_suspended, is_activated) when cached and fresh."""
    entry = _CACHE.get(tenant_id)
    if entry is None:
        return None
    cached_at, is_suspended, is_activated = entry
    if time.time() - cached_at >= _CACHE_TTL_SECONDS:
        _CACHE.pop(tenant_id, None)
        return None
    return is_suspended, is_activated


def set_tenant_access_status(
    tenant_id: int,
    *,
    is_suspended: bool,
    is_activated: bool,
) -> None:
    _CACHE[tenant_id] = (time.time(), is_suspended, is_activated)


def invalidate_tenant_access_cache(tenant_id: Optional[int] = None) -> None:
    """Clear one tenant or the entire activation cache."""
    if tenant_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(tenant_id, None)

"""In-memory cache for global SystemSettings (reduces DB hits during token creation)."""

from __future__ import annotations

import os
import time
from typing import Optional, Tuple

from app.conf.config import settings
from app.database.base import DefaultSessionLocal
from app.models.system_settings import SystemSettings

_CACHE: Optional[Tuple[float, Optional[SystemSettings]]] = None
_CACHE_TTL_SECONDS = int(os.getenv("SYSTEM_SETTINGS_CACHE_TTL", "300"))


def get_cached_system_settings() -> Optional[SystemSettings]:
    """Return cached SystemSettings row, refreshing from DB when stale."""
    global _CACHE

    now = time.time()
    if _CACHE is not None and now - _CACHE[0] < _CACHE_TTL_SECONDS:
        return _CACHE[1]

    db = DefaultSessionLocal()
    try:
        row = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
        _CACHE = (now, row)
        return row
    finally:
        db.close()


def invalidate_system_settings_cache() -> None:
    """Clear cached settings (call after admin updates system settings)."""
    global _CACHE
    _CACHE = None


def get_effective_access_token_expire_minutes() -> int:
    env_val = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
    if env_val:
        return int(env_val)

    try:
        row = get_cached_system_settings()
        if row is not None and row.access_token_expire_minutes is not None:
            return row.access_token_expire_minutes
    except Exception as exc:
        print(f"[SystemSettingsCache] access token expiry lookup failed: {exc}")

    return settings.ACCESS_TOKEN_EXPIRE_MINUTES


def get_effective_refresh_token_expire_days() -> int:
    env_val = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")
    if env_val:
        return int(env_val)

    try:
        row = get_cached_system_settings()
        if row is not None and row.refresh_token_expire_days is not None:
            return row.refresh_token_expire_days
    except Exception as exc:
        print(f"[SystemSettingsCache] refresh token expiry lookup failed: {exc}")

    return settings.REFRESH_TOKEN_EXPIRE_DAYS

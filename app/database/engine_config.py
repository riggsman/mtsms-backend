"""Shared SQLAlchemy engine configuration for global and tenant databases."""

from __future__ import annotations

import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.conf.config import settings


def get_engine_kwargs(*, for_tenant: bool = False) -> dict:
    """Build create_engine kwargs; tenant engines use a smaller pool by default."""
    if for_tenant:
        pool_size = settings.TENANT_DB_POOL_SIZE
        max_overflow = settings.TENANT_DB_MAX_OVERFLOW
    else:
        pool_size = settings.DB_POOL_SIZE
        max_overflow = settings.DB_MAX_OVERFLOW

    return {
        "pool_pre_ping": True,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
    }


def create_engine_with_retry(
    url: str,
    *,
    for_tenant: bool = False,
    max_retries: int = 10,
    retry_interval: int = 3,
):
    kwargs = get_engine_kwargs(for_tenant=for_tenant)
    for attempt in range(max_retries):
        try:
            engine = create_engine(url, **kwargs)
            engine.connect()
            return engine
        except OperationalError as exc:
            print(f"Database connection attempt {attempt + 1} failed: {exc}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                raise

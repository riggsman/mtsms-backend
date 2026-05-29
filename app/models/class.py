"""Backward-compat shim for legacy import path.

Canonical model lives in `app.models.classes`.
"""

from app.models.classes import Class

__all__ = ["Class"]

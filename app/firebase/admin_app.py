"""
Single Firebase Admin SDK initialization for FCM (and optional other Admin APIs).

Credential resolution (first match wins):
1. FIREBASE_SERVICE_ACCOUNT_JSON — full JSON object as a string (e.g. containers).
2. FIREBASE_SERVICE_ACCOUNT_PATH — absolute or relative path to the downloaded key file.
3. Default files next to this module (`app/firebase/`):
   - `serviceAccount.json`, or
   - any `*firebase-adminsdk*.json` (if exactly one is present, the first after sort).

Safe to import from multiple modules; initializes at most once.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

_initialized = False

# Directory containing this file: app/firebase/
_FIREBASE_PKG_DIR = Path(__file__).resolve().parent


def _service_account_json_in_firebase_dir() -> Optional[str]:
    """
    Path to a service account JSON placed in app/firebase/ (typical Firebase download).
    """
    preferred = _FIREBASE_PKG_DIR / "serviceAccount.json"
    if preferred.is_file():
        return str(preferred)
    matches = sorted(_FIREBASE_PKG_DIR.glob("*firebase-adminsdk*.json"))
    if matches:
        return str(matches[0])
    return None


def _load_credential():
    from app.conf.config import settings

    raw_json = (getattr(settings, "FIREBASE_SERVICE_ACCOUNT_JSON", None) or "").strip()
    if raw_json:
        try:
            info = json.loads(raw_json)
            return credentials.Certificate(info)
        except json.JSONDecodeError as e:
            logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: %s", e)
            return None

    path = (getattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", None) or "").strip()
    if not path:
        path = (os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or "").strip()
    if path and os.path.isfile(path):
        return credentials.Certificate(path)

    local = _service_account_json_in_firebase_dir()
    if local:
        logger.info("Using Firebase service account file from app/firebase/: %s", local)
        return credentials.Certificate(local)

    return None


def ensure_firebase_admin_initialized() -> bool:
    """
    Initialize firebase_admin if credentials are configured and app not already initialized.
    Returns True if the default app exists and is usable after this call.
    """
    global _initialized
    if _initialized:
        try:
            firebase_admin.get_app()
            return True
        except ValueError:
            _initialized = False

    try:
        firebase_admin.get_app()
        _initialized = True
        return True
    except ValueError:
        pass

    cred = _load_credential()
    if cred is None:
        logger.debug("Firebase Admin not configured (no service account path or JSON).")
        return False

    try:
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("Firebase Admin SDK initialized for FCM.")
        return True
    except ValueError as e:
        # Already initialized elsewhere in the same process
        if "already exists" in str(e).lower():
            _initialized = True
            return True
        logger.error("Firebase Admin initialize_app failed: %s", e)
        return False
    except Exception as e:
        logger.error("Firebase Admin initialize_app failed: %s", e)
        return False


def is_firebase_admin_ready() -> bool:
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        return ensure_firebase_admin_initialized()

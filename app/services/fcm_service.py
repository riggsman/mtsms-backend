"""
Firebase Cloud Messaging: send web push and maintain tokens.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Set

from sqlalchemy.orm import Session

from app.firebase.admin_app import ensure_firebase_admin_initialized, is_firebase_admin_ready
from app.helpers.user_roles import user_has_any_role, user_has_role, user_roles_list
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.models.user_push_token import UserPushToken

logger = logging.getLogger(__name__)

# FCM multicast batch size (Firebase limit is 500)
_FCM_BATCH = 500


def _multicast_message_kwargs(tokens: List[str], title: str, body: str, data: Optional[Dict[str, str]]) -> Dict[str, Any]:
    """Build MulticastMessage kwargs with explicit webpush (improves browser delivery vs notification-only)."""
    from firebase_admin import messaging

    t = (title or "")[:200]
    b = (body or "")[:1000]
    notif = messaging.Notification(title=t, body=b)
    kwargs: Dict[str, Any] = {"tokens": tokens, "notification": notif}
    try:
        kwargs["webpush"] = messaging.WebpushConfig(
            notification=messaging.WebpushNotification(title=t, body=b),
        )
    except Exception:
        pass
    if data:
        kwargs["data"] = {k: str(v) for k, v in data.items()}
    return kwargs


def is_fcm_messaging_enabled_globally(global_db: Session) -> bool:
    # Check env var first (higher priority)
    env_enabled = os.getenv("FIREBASE_MESSAGING_ENABLED", "").lower()
    if env_enabled == "true":
        return True
    
    # Fall back to database
    row = global_db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    if not row:
        return False
    return bool(getattr(row, "firebase_messaging_enabled", False))


def _recipient_user_ids_for_announcement(
    tenant_db: Session,
    institution_id: int,
    target_audience: str,
) -> Set[int]:
    audience = (target_audience or "all").strip().lower()
    users = (
        tenant_db.query(User)
        .filter(
            User.institution_id == institution_id,
            User.deleted_at.is_(None),
            User.is_active == "active",
        )
        .all()
    )
    out: Set[int] = set()
    for u in users:
        roles = set(user_roles_list(u))
        if audience == "all":
            out.add(u.id)
        elif audience == "students":
            if user_has_role(u, "student"):
                out.add(u.id)
        elif audience == "staff":
            if user_has_any_role(
                u,
                ["staff", "teacher", "lecturer", "admin", "super_admin", "secretary"],
            ):
                out.add(u.id)
        else:
            out.add(u.id)
    return out


def get_fcm_tokens_for_users(tenant_db: Session, user_ids: Sequence[int]) -> List[str]:
    if not user_ids:
        return []
    rows = (
        tenant_db.query(UserPushToken.token)
        .filter(UserPushToken.user_id.in_(list(user_ids)))
        .all()
    )
    return list({r[0] for r in rows if r and r[0]})


def delete_tokens_strings(tenant_db: Session, tokens: Sequence[str]) -> int:
    if not tokens:
        return 0
    unique = list({t for t in tokens if t})
    deleted = (
        tenant_db.query(UserPushToken)
        .filter(UserPushToken.token.in_(unique))
        .delete(synchronize_session=False)
    )
    tenant_db.commit()
    return int(deleted or 0)


def send_web_push_for_user_ids(
    tenant_db: Session,
    global_db: Session,
    user_ids: Sequence[int],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> None:
    """
    Best-effort FCM send. Swallows errors so domain logic (e.g. announcements) is not blocked.
    """
    try:
        if not is_fcm_messaging_enabled_globally(global_db):
            return
        if not ensure_firebase_admin_initialized():
            logger.debug("FCM send skipped: Firebase Admin not configured.")
            return
        ids = list({int(x) for x in user_ids if x is not None})
        if not ids:
            return
        tokens = get_fcm_tokens_for_users(tenant_db, ids)
        if not tokens:
            return
        _invalid = _send_multicast_batches_core(tokens, title, body, data)
        if _invalid:
            try:
                delete_tokens_strings(tenant_db, _invalid)
            except Exception as del_err:
                logger.warning("Failed to prune invalid FCM tokens: %s", del_err)
    except Exception as e:
        logger.warning("FCM send_web_push_for_user_ids failed: %s", e, exc_info=True)


def send_announcement_push(
    tenant_db: Session,
    global_db: Session,
    institution_id: int,
    target_audience: str,
    title: str,
    body: str,
    announcement_id: int,
    exclude_user_id: Optional[int] = None,
) -> None:
    user_ids = _recipient_user_ids_for_announcement(tenant_db, institution_id, target_audience)
    if exclude_user_id is not None:
        user_ids.discard(int(exclude_user_id))
    data = {
        "type": "announcement",
        "announcementId": str(announcement_id),
        "institutionId": str(institution_id),
    }
    send_web_push_for_user_ids(tenant_db, global_db, sorted(user_ids), title, body, data=data)


def _send_multicast_batches_core(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]],
) -> List[str]:
    """
    Send FCM to token batches. Returns list of invalid registration tokens to prune.
    Caller may delete invalid tokens from DB.
    """
    from firebase_admin import messaging

    if not ensure_firebase_admin_initialized():
        logger.error("FCM send failed: Firebase Admin not initialized. Check service account config.")
        return tokens

    if not tokens:
        logger.warning("FCM send: no tokens provided")
        return []

    invalid: List[str] = []

    try:
        import firebase_admin

        _proj = getattr(firebase_admin.get_app(), "project_id", None) or "unknown"
    except Exception:
        _proj = "unknown"
    logger.info("FCM sending to %d tokens (project: %s)", len(tokens), _proj)

    for i in range(0, len(tokens), _FCM_BATCH):
        batch = tokens[i : i + _FCM_BATCH]
        kwargs = _multicast_message_kwargs(batch, title, body, data)
        msg = messaging.MulticastMessage(**kwargs)

        try:
            resp = messaging.send_each_for_multicast(msg)
        except AttributeError:
            resp = messaging.send_multicast(msg)

        if hasattr(resp, "responses"):
            for idx, r in enumerate(resp.responses):
                if getattr(r, "success", False):
                    continue
                exc = getattr(r, "exception", None)
                err_text = (str(exc) or "").lower()
                code = getattr(exc, "code", None) if exc else None
                if code in (
                    "messaging/registration-token-not-registered",
                    "messaging/invalid-registration-token",
                ) or "not-registered" in err_text or "invalid-registration" in err_text or "unregistered" in err_text:
                    if idx < len(batch):
                        invalid.append(batch[idx])

    return invalid


def _send_multicast_batches_with_counts(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]],
) -> tuple[int, int, List[str]]:
    """Returns (success_count, failure_count, invalid_tokens)."""
    from firebase_admin import messaging

    success = 0
    failure = 0
    invalid: List[str] = []
    for i in range(0, len(tokens), _FCM_BATCH):
        batch = tokens[i : i + _FCM_BATCH]
        kwargs = _multicast_message_kwargs(batch, title, body, data)
        msg = messaging.MulticastMessage(**kwargs)

        try:
            resp = messaging.send_each_for_multicast(msg)
            logger.info("FCM response: success_count=%d, failure_count=%d", 
                getattr(resp, 'success_count', 'N/A'), 
                getattr(resp, 'failure_count', 'N/A'))
        except AttributeError:
            resp = messaging.send_multicast(msg)

        if hasattr(resp, "responses"):
            for idx, r in enumerate(resp.responses):
                if getattr(r, "success", False):
                    success += 1
                else:
                    failure += 1
                    exc = getattr(r, "exception", None)
                    err_text = str(exc) if exc else ""
                    logger.warning("FCM token %d/%d failed: %s", idx, len(batch), err_text[:200])
                    code = getattr(exc, "code", None) if exc else None
                    if code in (
                        "messaging/registration-token-not-registered",
                        "messaging/invalid-registration-token",
                    ) or "not-registered" in err_text or "invalid-registration" in err_text or "unregistered" in err_text:
                        if idx < len(batch):
                            invalid.append(batch[idx])

    return success, failure, invalid


def send_fcm_test_push_to_users(
    tenant_db: Session,
    global_db: Session,
    user_ids: Sequence[int],
    title: str = "MTSMS test",
    body: str = "If you see this, web push is working.",
) -> dict:
    """
    Send one FCM test to the given users' registered devices. Returns a dict for the API (not swallowed).
    """
    if not is_fcm_messaging_enabled_globally(global_db):
        return {
            "ok": False,
            "reason": "firebase_disabled",
            "success": 0,
            "failure": 0,
            "tokens_targeted": 0,
        }
    ids = list({int(x) for x in user_ids if x is not None})
    if not ids:
        return {
            "ok": False,
            "reason": "no_user_ids",
            "success": 0,
            "failure": 0,
            "tokens_targeted": 0,
        }
    tokens = get_fcm_tokens_for_users(tenant_db, ids)
    if not tokens:
        return {
            "ok": False,
            "reason": "no_tokens",
            "success": 0,
            "failure": 0,
            "tokens_targeted": 0,
        }
    if not ensure_firebase_admin_initialized():
        return {
            "ok": False,
            "reason": "admin_sdk_not_configured",
            "success": 0,
            "failure": 0,
            "tokens_targeted": len(tokens),
        }
    try:
        data = {"type": "test"}
        success, fail, invalid = _send_multicast_batches_with_counts(tokens, title, body, data)
        logger.info("FCM test push result: success=%d, failure=%d, invalid=%s", success, fail, invalid)
        if fail > 0:
            logger.warning("FCM failures: likely tokens from wrong project or expired. tokens_targeted=%d", len(tokens))
        if invalid:
            try:
                delete_tokens_strings(tenant_db, invalid)
            except Exception as e:
                logger.warning("Failed to prune invalid FCM tokens after test: %s", e)
        return {
            "ok": success > 0,
            "reason": None if success > 0 else ("all_failed" if fail else None),
            "success": success,
            "failure": fail,
            "tokens_targeted": len(tokens),
        }
    except Exception as e:
        logger.exception("FCM test push failed: %s", e)
        return {
            "ok": False,
            "reason": "send_error",
            "detail": str(e)[:500],
            "success": 0,
            "failure": 0,
            "tokens_targeted": len(tokens),
        }


def send_fcm_notification_to_users(
    tenant_db: Session,
    global_db: Session,
    user_ids: Sequence[int],
    title: str = "MTSMS Notification",
    body: str = "",
) -> dict:
    """
    Send an FCM notification to the given users' registered devices.
    """
    if not is_fcm_messaging_enabled_globally(global_db):
        return {
            "ok": False,
            "reason": "firebase_disabled",
            "success": 0,
            "failure": 0,
            "tokens_targeted": 0,
        }
    ids = list({int(x) for x in user_ids if x is not None})
    if not ids:
        return {
            "ok": False,
            "reason": "no_user_ids",
            "success": 0,
            "failure": 0,
            "tokens_targeted": 0,
        }
    tokens = get_fcm_tokens_for_users(tenant_db, ids)
    if not tokens:
        return {
            "ok": False,
            "reason": "no_tokens",
            "success": 0,
            "failure": 0,
            "tokens_targeted": 0,
        }
    if not ensure_firebase_admin_initialized():
        return {
            "ok": False,
            "reason": "admin_sdk_not_configured",
            "success": 0,
            "failure": 0,
            "tokens_targeted": len(tokens),
        }
    try:
        data = {"type": "notification"}
        success, fail, invalid = _send_multicast_batches_with_counts(tokens, title, body, data)
        logger.info("FCM notification result: success=%d, failure=%d", success, fail)
        if invalid:
            try:
                delete_tokens_strings(tenant_db, invalid)
            except Exception as e:
                logger.warning("Failed to prune invalid FCM tokens: %s", e)
        return {
            "ok": success > 0,
            "reason": None if success > 0 else "all_failed",
            "success": success,
            "failure": fail,
            "tokens_targeted": len(tokens),
        }
    except Exception as e:
        logger.exception("FCM notification failed: %s", e)
        return {
            "ok": False,
            "reason": "send_error",
            "detail": str(e)[:500],
            "success": 0,
            "failure": 0,
            "tokens_targeted": len(tokens),
        }

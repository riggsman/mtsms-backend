from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import logging

from app.models.user import User
from app.models.system_config import SystemConfig
from app.authentication.authenticator import hash_password
from app.conf.config import settings

logger = logging.getLogger(__name__)

DEFAULT_SUPERADMIN_EMAIL = "support@riggsmantechnologies.com"
DEFAULT_SUPERADMIN_USERNAME = "superadmin"
DEFAULT_SUPERADMIN_PASSWORD = "superadmin"
STARTUP_SEED_ONCE_KEY = "startup_seed_completed_once"


def _truncate_all_tables(session: Session) -> None:
    """Dangerous: wipes every table except alembic_version. Dev-only."""
    session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    result = session.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result]
    for table in tables:
        if table == "alembic_version":
            continue
        session.execute(text(f"TRUNCATE TABLE `{table}`"))
        logger.warning("Startup seed truncated table: %s", table)
    session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    session.commit()


def _ensure_default_superadmin(session: Session) -> None:
    """Create default system superadmin if no user with that email/username exists."""
    existing = (
        session.query(User)
        .filter(
            (User.email == DEFAULT_SUPERADMIN_EMAIL)
            | (User.username == DEFAULT_SUPERADMIN_USERNAME)
        )
        .first()
    )
    if existing:
        return
    admin_data = {
        "firstname": "System",
        "lastname": "SuperAdmin",
        "email": DEFAULT_SUPERADMIN_EMAIL,
        "username": DEFAULT_SUPERADMIN_USERNAME,
        "password": hash_password(DEFAULT_SUPERADMIN_PASSWORD),
        "role": ["system_super_admin"],
        "user_type": "SYSTEM",
        "is_active": "active",
        "gender": "male",
        "address": "System",
        "phone": "+0000000000",
        "created_at": datetime.utcnow(),
        "language": "en",
    }
    session.add(User(**admin_data))
    session.commit()
    logger.info(
        "Default superadmin created: username=%s (set STARTUP_TRUNCATE_ALL=false in production)",
        DEFAULT_SUPERADMIN_USERNAME,
    )


def _is_startup_seed_already_completed(session: Session) -> bool:
    row = (
        session.query(SystemConfig)
        .filter(SystemConfig.key == STARTUP_SEED_ONCE_KEY)
        .first()
    )
    return bool(row and str(row.value).lower() in {"1", "true", "yes"})


def _mark_startup_seed_completed(session: Session) -> None:
    row = (
        session.query(SystemConfig)
        .filter(SystemConfig.key == STARTUP_SEED_ONCE_KEY)
        .first()
    )
    if row:
        row.value = "true"
        row.description = "Startup seed completed successfully at least once."
        session.add(row)
    else:
        session.add(
            SystemConfig(
                key=STARTUP_SEED_ONCE_KEY,
                value="true",
                description="Startup seed completed successfully at least once.",
            )
        )
    session.commit()


def run_startup_seed(session: Session) -> None:
    """
    Optional dev wipe + idempotent platform seed.

    This seed now runs only once successfully per database lifecycle.
    After first success, future restarts skip this function entirely.

    - If STARTUP_TRUNCATE_ALL=true and first run: TRUNCATE every table except alembic_version, then seed.
    - Otherwise on first run: seed defaults without truncation.
    """
    try:
        if _is_startup_seed_already_completed(session):
            logger.info("Startup seed already completed earlier; skipping on this restart.")
            return

        if settings.STARTUP_TRUNCATE_ALL:
            logger.warning(
                "STARTUP_TRUNCATE_ALL is enabled: wiping all application tables (dev reset)."
            )
            _truncate_all_tables(session)
            _ensure_default_superadmin(session)
        else:
            _ensure_default_superadmin(session)

        from app.models.subscription_plan import SubscriptionPlan  # noqa: F401
        from app.routes.subscription_plans import ensure_default_subscription_plans

        ensure_default_subscription_plans(session)
        plan_count = session.query(SubscriptionPlan).count()
        logger.info("Subscription plans in database: %s", plan_count)
        _mark_startup_seed_completed(session)
    except Exception as e:
        session.rollback()
        logger.error("Startup seed failed: %s", e, exc_info=True)
        raise

from sqlalchemy.orm import Session

from scripts.populate_classes import seed_default_admin_user, seed_default_classes
from scripts.seed_data import run_seed


def run_startup_seed(session: Session) -> None:
    """
    Centralized startup seeding orchestration.
    Safe to run on every startup; seeders are idempotent.
    """
    seed_default_classes(session)
    seed_default_admin_user(session)
    run_seed()

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.conf.config import settings
from app.database.engine_config import create_engine_with_retry

engine = create_engine_with_retry(settings.DATABASE_URL)
DefaultSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
DefaultBase = declarative_base()
Base = DefaultBase


def get_db_session():
    db_session = DefaultSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

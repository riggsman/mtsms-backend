import time
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from app.conf.config import settings

def create_engine_with_retry(url, max_retries=10, retry_interval=3):
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_timeout=30,
            )
            engine.connect()
            return engine
        except OperationalError as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                raise

engine = create_engine_with_retry(settings.DATABASE_URL)
DefaultSessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
DefaultBase = declarative_base()
Base = DefaultBase

def get_db_session():
    db_session = DefaultSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
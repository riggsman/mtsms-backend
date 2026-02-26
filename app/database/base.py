from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.conf.config import settings

engine = create_engine(settings.DATABASE_URL)
DefaultSessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
DefaultBase = declarative_base()

def get_db_session():
    db_session = DefaultSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
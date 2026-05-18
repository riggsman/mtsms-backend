import time
from typing import Optional
try:
    from fastapi import Depends, HTTPException
except ImportError:
    class Depends:
        def __init__(self, dependency=None): pass
    class HTTPException(Exception):
        def __init__(self, status_code=500, detail=None): pass
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import OperationalError
from app.database.base import get_db_session, DefaultSessionLocal

get_db = get_db_session
from app.helpers.formater import Format_Helper
from app.helpers.mysql_connection import build_tenant_database_url, get_mysql_params
from app.models.tenant import Tenant
from app.models.system_config import SystemConfig

try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    Error = Exception
from sqlalchemy.ext.declarative import declarative_base

BaseModel_Base = declarative_base()

tenant_engine = {}

_db_mode_cache = None


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


async def create_tenant_database(db_name, user: str | None = None, password: str | None = None):
    try:
        params = get_mysql_params()
        host = params["host"]
        user = user if user is not None else params["user"]
        password = password if password is not None else params["password"]
        connection = mysql.connector.connect(
            host=host,
            port=params["port"],
            user=user,
            password=password,
        )

        cursor = connection.cursor()
        tenant_db_name = Format_Helper(db_name).replace_space_with_underscore()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{tenant_db_name}`")
        print(f"Database '{tenant_db_name}' created successfully.")

        engine = create_engine_with_retry(build_tenant_database_url(tenant_db_name))
        BaseModel_Base.metadata.create_all(bind=engine)

        cursor.close()
        connection.close()
        url = build_tenant_database_url(tenant_db_name)
        print(url)
        return url

    except Error as e:
        print("Error while connecting to MySQL:", e)
        return None


def get_database_mode() -> str:
    """
    Get the current database architecture mode.
    Returns 'shared' or 'multi_tenant'.
    Defaults to 'shared' if not set.
    """
    global _db_mode_cache
    
    # Return cached value if available
    if _db_mode_cache is not None:
        return _db_mode_cache
    
    # Query the global database for the mode
    db = DefaultSessionLocal()
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == 'database_mode').first()
        if config and config.value:
            _db_mode_cache = config.value
            return config.value
        else:
            # Default to shared if not configured
            _db_mode_cache = 'shared'
            # Initialize with shared mode if not set
            try:
                new_config = SystemConfig(
                    key='database_mode',
                    value='shared',
                    description='Database architecture mode: shared (single database) or multi_tenant (separate databases per tenant). Default: shared'
                )
                db.add(new_config)
                db.commit()
            except Exception as init_error:
                db.rollback()
                print(f"Warning: Could not initialize database mode: {init_error}")
            return 'shared'
    except Exception as e:
        print(f"Error getting database mode: {e}")
        # Default to shared on error
        _db_mode_cache = 'shared'
        return 'shared'
    finally:
        db.close()


def set_database_mode(mode: str, db: Session):
    """
    Set the database architecture mode.
    mode: 'shared' or 'multi_tenant'
    """
    global _db_mode_cache
    
    if mode not in ['shared', 'multi_tenant']:
        raise ValueError("Mode must be 'shared' or 'multi_tenant'")
    
    config = db.query(SystemConfig).filter(SystemConfig.key == 'database_mode').first()
    if config:
        config.value = mode
    else:
        config = SystemConfig(
            key='database_mode',
            value=mode,
            description='Database architecture mode: shared (single database) or multi_tenant (separate databases per tenant)'
        )
        db.add(config)
    
    db.commit()
    _db_mode_cache = mode  # Update cache


def get_shared_db():
    """
    Returns a sessionmaker for the shared database (used when in shared mode).
    """
    from app.database.base import DefaultSessionLocal
    return DefaultSessionLocal


def get_tenant_db(tenant_name: str):
    """
    Returns a sessionmaker for the tenant-specific database.
    Used when in multi_tenant mode.
    """
    # Check if the tenant database already has an engine
    if tenant_name in tenant_engine:
        return tenant_engine[tenant_name]

    # Validate the tenant name (optional, if you have a list of valid tenants)
    # For example, you could query a central database to validate the tenant.
    # Here, we assume the tenant name is valid if it's provided.

    try:
        tenant_db_name = Format_Helper(tenant_name).replace_space_with_underscore()
        # Create a new engine for the tenant
        engine = create_engine_with_retry(build_tenant_database_url(tenant_db_name))
        print(f"Created new engine for tenant '{tenant_db_name}'")

        # Create a sessionmaker for the tenant
        TenantSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        tenant_engine[tenant_name] = TenantSessionLocal

        # Create all tables (if they don't exist)
        BaseModel_Base.metadata.create_all(bind=engine)

        return TenantSessionLocal

    except Exception as e:
        print(f"Error creating engine or sessionmaker for tenant '{tenant_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to establish database connection")


def get_db_session_for_mode(tenant_name: str = None):
    """
    Get the appropriate database session based on the current mode.
    If shared mode: returns shared database session
    If multi_tenant mode: returns tenant-specific database session
    """
    mode = get_database_mode()
    
    if mode == 'shared':
        return get_shared_db()
    else:
        if not tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name is required in multi-tenant mode")
        return get_tenant_db(tenant_name)


def create_standalone_db_session(tenant_name: Optional[str] = None) -> Session:
    """
    New Session for background/async work (never share a request-scoped Session across threads).
    Matches shared vs multi-tenant like get_db. Caller must close the session.
    """
    mode_normalized = str(get_database_mode() or "shared").lower().strip()
    is_multi_tenant = mode_normalized in (
        "multi_tenant",
        "multi-tenant",
        "multitenant",
        "isolated",
    )
    if not is_multi_tenant:
        return get_shared_db()()
    if tenant_name:
        return get_tenant_db(tenant_name)()
    return get_shared_db()()
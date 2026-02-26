from logging.config import fileConfig
import sys
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database bases and all models
from app.database.base import DefaultBase, engine
from app.database.sessionManager import BaseModel_Base
from app.conf.config import settings

# Import all models to ensure they're registered with their Base classes
# Models using DefaultBase (global database)
from app.models.tenant import Tenant
from app.models.system_config import SystemConfig

# Models using BaseModel_Base (tenant/shared database)
from app.models.department import Department
from app.models.academic_year import AcademicYear
from app.models.guardian import Guardian
from app.models.course import Course
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.models.complaint import Complaint
from app.models.assignment import Assignment
from app.models.student_record import StudentRecord
from app.models.enrollment import Enrollment
from app.models.note import Note
from app.models.announcement import Announcement
from app.models.activity import Activity
from app.models.tenant_settings import TenantSettings

# Import Class model (class is a reserved keyword)
import importlib
_class_module = importlib.import_module('app.models.class')

# Combine metadata from both bases into a single metadata object
# This allows Alembic to detect all tables from both bases
from sqlalchemy import MetaData

# Create a combined metadata object
combined_metadata = MetaData()

# Copy all tables from DefaultBase.metadata
for table in DefaultBase.metadata.tables.values():
    combined_metadata._add_table(table.name, table.schema, table)

# Copy all tables from BaseModel_Base.metadata
for table in BaseModel_Base.metadata.tables.values():
    if table.name not in combined_metadata.tables:
        combined_metadata._add_table(table.name, table.schema, table)

target_metadata = combined_metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with the one from settings if not set in ini
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the engine from base.py or create from config
    url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    config.set_main_option("sqlalchemy.url", url)
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

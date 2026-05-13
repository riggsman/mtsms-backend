"""Rollback migration to remove cache_version column from system_settings table"""
from sqlalchemy import create_engine, text
import sys
import os

# Add the parent directory to the path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conf.config import settings

def rollback_migration():
    print("=" * 60)
    print("Rollback: Remove cache_version column from system_settings")
    print("=" * 60)
    
    # Create engine from settings
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("SHOW COLUMNS FROM system_settings LIKE 'cache_version'"))
        column_exists = result.fetchone()
        
        if not column_exists:
            print("Column 'cache_version' does not exist in system_settings. Nothing to rollback.")
            return
        
        # Remove the cache_version column
        print("Removing 'cache_version' column from system_settings table...")
        conn.execute(text(
            'ALTER TABLE system_settings DROP COLUMN cache_version'
        ))
        
        conn.commit()
        print("Column removed successfully!")
    
    # Update alembic version table if it exists
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'alembic_version'"))
            if result.fetchone():
                conn.execute(text(
                    "DELETE FROM alembic_version WHERE version_num = 'add_cache_version_column'"
                ))
                conn.commit()
                print("Alembic version updated.")
    except Exception as e:
        print(f"Note: Could not update alembic version: {e}")
    
    print("=" * 60)
    print("Rollback completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    rollback_migration()

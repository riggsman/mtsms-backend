    """Run migration to add cache_version column to system_settings table"""
from sqlalchemy import create_engine, text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.conf.config import settings

def run_migration():
    print("=" * 60)
    print("Migration: Add cache_version column to system_settings")
    print("=" * 60)
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Get existing columns
        result = conn.execute(text("DESCRIBE system_settings"))
        existing_columns = [row[0] for row in result.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Add cache_version if not exists
        if 'cache_version' in existing_columns:
            print("Column 'cache_version' already exists. Skipping.")
        else:
            print("Adding 'cache_version' column...")
            conn.execute(text(
                'ALTER TABLE system_settings ADD COLUMN cache_version VARCHAR(64) DEFAULT "1" NOT NULL'
            ))
            conn.commit()
            print("Column 'cache_version' added successfully!")
        
        # Check/update alembic version
        try:
            result = conn.execute(text("SHOW TABLES LIKE 'alembic_version'"))
            if result.fetchone():
                conn.execute(text(
                    "INSERT INTO alembic_version (version_num) VALUES ('add_cache_version_column') "
                    "ON DUPLICATE KEY UPDATE version_num = version_num"
                ))
                conn.commit()
                print("Alembic version updated.")
        except Exception as e:
            print(f"Note: {e}")
    
    print("=" * 60)
    print("Migration completed!")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()

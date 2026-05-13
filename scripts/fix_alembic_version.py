"""fix_alembic_version

Manually stamp the alembic_version table to 20260423_add_leave_utility_requests

Usage: python scripts/fix_alembic_version.py (run from backend directory)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

try:
    from app.database.sessionManager import DefaultSessionLocal
    from sqlalchemy import text
    
    def stamp():
        with DefaultSessionLocal() as session:
            try:
                # Try MySQL first
                result = session.execute(text("SELECT version_num FROM alembic_version"))
                current = result.scalar()
                print(f"Current alembic_version: {current}")
                
                # Check tables
                result = session.execute(text("SHOW TABLES LIKE 'leave_requests'"))
                has_leaves = result.fetchone() is not None
                result = session.execute(text("SHOW TABLES LIKE 'utility_requests'"))
                has_utils = result.fetchone() is not None
                
                print(f"leave_requests exists: {has_leaves}")
                print(f"utility_requests exists: {has_utils}")
                
                if has_leaves and has_utils:
                    session.execute(text("UPDATE alembic_version SET version_num = '20260423_add_leave_utility_requests'"))
                    session.commit()
                    print("SUCCESS: Stamped to 20260423_add_leave_utility_requests")
                else:
                    print("Tables don't exist - run: alembic upgrade head")
                    
            except Exception as e:
                print(f"Error: {e}")
                
except ImportError as e:
    print(f"Import error: {e}")
    print("Ensure you're running from the backend directory with correct environment")
"""Fix alembic version stamp

This script fixes the alembic_version table to stamp the correct migration revision
"""
from app.database.sessionManager import DefaultSessionLocal
from app.models.base import Base
from sqlalchemy import text

def stamp_current_revision():
    with DefaultSessionLocal() as session:
        # First check current state
        result = session.execute(text("SELECT version_num FROM alembic_version"))
        current = result.scalar()
        print(f"Current alembic_version: {current}")
        
        # Check if tables exist
        result = session.execute(text("SHOW TABLES LIKE 'leave_requests'"))
        leaves_exists = result.fetchone() is not None
        result = session.execute(text("SHOW TABLES LIKE 'utility_requests'"))
        utilities_exists = result.fetchone() is not None
        
        print(f"leave_requests table exists: {leaves_exists}")
        print(f"utility_requests table exists: {utilities_exists}")
        
        if leaves_exists and utilities_exists and current == '20260423_add_leave_utility_requests':
            # Already stamped correctly
            print("Already correctly stamped!")
            return
            
        # Update to the correct revision
        if (leaves_exists and utilities_exists and 
            (current == 'e2488cc993ab_' or current is None)):
            session.execute(text("UPDATE alembic_version SET version_num = '20260423_add_leave_utility_requests'"))
            session.commit()
            print("Updated alembic_version to 20260423_add_leave_utility_requests")
        else:
            print(f"Unexpected state - please check manually. Current: {current}")

if __name__ == "__main__":
    stamp_current_revision()
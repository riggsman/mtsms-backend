"""
Script to create database tables without starting the server
Run this before running seed_data.py if you haven't started the server yet
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import DefaultBase, engine, DefaultSessionLocal
from app.database.sessionManager import BaseModel_Base, set_database_mode

# Import all models to ensure they're registered with their respective Base classes
import importlib

# Import models that use DefaultBase (global database)
from app.models.tenant import Tenant
from app.models.system_config import SystemConfig

# Import models that use BaseModel_Base (tenant/shared database)
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

# Import Class model (class is a reserved keyword, so use importlib)
_class_module = importlib.import_module('app.models.class')

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    try:
        # Create tables for DefaultBase (e.g., tenants)
        DefaultBase.metadata.create_all(bind=engine)
        print("✓ Created DefaultBase tables (tenants, etc.)")
        
        # Create tables for BaseModel_Base (most models)
        BaseModel_Base.metadata.create_all(bind=engine)
        print("✓ Created BaseModel_Base tables (departments, courses, etc.)")
        
        # Initialize database mode to 'shared' by default
        db = DefaultSessionLocal()
        try:
            config = db.query(SystemConfig).filter(SystemConfig.key == 'database_mode').first()
            if not config:
                set_database_mode('shared', db)
                print("✓ Initialized database mode to 'shared' (default)")
            else:
                print(f"✓ Database mode already set to: {config.value}")
        except Exception as e:
            print(f"⚠ Warning: Could not initialize database mode: {e}")
        finally:
            db.close()
        
        print("\n✓ Database tables created successfully!")
        print("✓ Database mode: shared (default)")
        print("You can now run the seed script: python scripts/seed_data.py")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()

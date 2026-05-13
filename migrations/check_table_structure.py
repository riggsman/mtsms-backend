"""Check system_settings table structure"""
from sqlalchemy import create_engine, text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.conf.config import settings

def check_table():
    print("Checking system_settings table structure...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("DESCRIBE system_settings"))
        columns = result.fetchall()
        
        print("\nCurrent columns in system_settings table:")
        print("-" * 50)
        for col in columns:
            print(f"  {col[0]}: {col[1]}")
        print("-" * 50)
        
        # Check for cache_version
        has_cache_version = any(col[0] == 'cache_version' for col in columns)
        print(f"\nHas cache_version column: {has_cache_version}")

if __name__ == "__main__":
    check_table()

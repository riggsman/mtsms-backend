import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DATABASE_URL from environment
database_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root@localhost:3306/mtsms')

# Create engine
engine = create_engine(database_url)

def apply_migration():
    print(f"Connecting to {database_url}...")
    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("SHOW COLUMNS FROM courses LIKE 'instructor_id'"))
            if not result.fetchone():
                print("Adding instructor_id column to courses table...")
                conn.execute(text("ALTER TABLE courses ADD COLUMN instructor_id INTEGER NULL AFTER level_id"))
                conn.commit()
                print("Column instructor_id added successfully.")
            else:
                print("Column instructor_id already exists in courses table.")
            
    except Exception as e:
        print(f"Error applying migration: {e}")

if __name__ == "__main__":
    apply_migration()

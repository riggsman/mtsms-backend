# Database Setup Scripts

This directory contains scripts for setting up and populating the database.

## Database Migrations with Alembic

This project uses Alembic for database migrations. See `ALEMBIC_SETUP.md` in the root directory for detailed instructions.

### Quick Start

1. **Check current migration status:**
   ```bash
   alembic current
   ```

2. **Apply all pending migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Create a new migration:**
   ```bash
   alembic revision --autogenerate -m "description of changes"
   ```

4. **View migration history:**
   ```bash
   alembic history
   ```

---

## Database Seeding Script

This script populates the database with initial data for testing and development.

## Prerequisites

1. Make sure your database is set up and configured
2. Ensure your virtual environment is activated
3. **Database tables must be created first** - The tables are automatically created when you start the FastAPI server, OR you can create them manually (see below)

## How to Run

### Step 1: Create Database Tables

**Option A: Start the server (recommended)**
The tables are automatically created when the FastAPI server starts. Run:
```bash
cd "E:\PERSONAL\PERSONAL WORK\MTSMS"
env\Scripts\activate  # Windows
# or: source env/bin/activate  # Linux/Mac

# Start the server (this creates the tables)
uvicorn server:app --reload
```
Wait for the server to start, then stop it (Ctrl+C). The tables will now exist.

**Option B: Create tables manually**
Create a script to create tables without starting the server (see troubleshooting section).

### Step 2: Run the Seed Script

1. Navigate to the project root directory:
```bash
cd "E:\PERSONAL\PERSONAL WORK\MTSMS"
```

2. Activate your virtual environment (if not already activated):
```bash
# Windows
env\Scripts\activate

# Linux/Mac
source env/bin/activate
```

3. Run the seed script:
```bash
python scripts/seed_data.py
```

### Option 2: Using Python module syntax

```bash
python -m scripts.seed_data
```

### Option 3: From the scripts directory

```bash
cd scripts
python seed_data.py
```

## What the Script Does

The script will create:

1. **Departments** - Mathematics, Science, English, Computer Science, etc.
2. **Academic Years** - 2023-2024, 2024-2025
3. **Classes** - Grade 8, 9, 10, 11
4. **Guardians** - Sample guardian records for students
5. **Courses** - Mathematics 101, Science Lab, English Literature, Computer Science
6. **Schedules** - Sample class schedules
7. **Teachers** - Prof. Smith, Dr. Johnson, Ms. Williams, Prof. Davis
8. **Students** - Sample student records
9. **Assignments** - Sample assignments for courses
10. **Users** - Admin, Super Admin, Secretary users

## Default Credentials

After running the seed script, you can login with:

- **Admin User:**
  - Username: `admin`
  - Password: `admin123`
  - Role: `admin`

- **Super Admin:**
  - Username: `superadmin`
  - Password: `superadmin123`
  - Role: `super_admin`

- **Secretary:**
  - Username: `secretary`
  - Password: `secretary123`
  - Role: `secretary`

## Troubleshooting

### Error: "No module named 'app'"
- Make sure you're running from the project root directory
- Ensure your virtual environment is activated
- Check that the PYTHONPATH includes the project root

### Error: "Table does not exist"
- **Solution 1**: Start the FastAPI server first (it creates tables on startup), then stop it and run the seed script
- **Solution 2**: Run the table creation script:
  ```bash
  python scripts/create_tables.py
  ```
- Check your database connection settings in `app/conf/config.py`
- Ensure your MySQL database exists and is accessible

### Error: "Tenant not found"
- The script uses the default database session
- Make sure your database is properly configured
- Check that the tenant table exists

## Notes

- The script uses `institution_id: 1` by default for users
- Department IDs are auto-generated
- The script checks for existing records to avoid duplicates
- All passwords are hashed using the authenticator module

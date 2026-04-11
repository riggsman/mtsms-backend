"""Run migration to add is_due and is_overdue columns"""
from sqlalchemy import create_engine, text

# Create engine
engine = create_engine('mysql+pymysql://root:@localhost/mtsms')

# Execute the ALTER TABLE directly
with engine.connect() as conn:
    conn.execute(text('ALTER TABLE fee_installments ADD COLUMN is_due BOOLEAN NOT NULL DEFAULT FALSE'))
    conn.execute(text('ALTER TABLE fee_installments ADD COLUMN is_overdue BOOLEAN NOT NULL DEFAULT FALSE'))
    conn.commit()
    print('Columns added successfully')

# Update the version table
with engine.connect() as conn:
    conn.execute(text("DELETE FROM alembic_version WHERE version_num = '5cc50cad6579'"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('add_is_due_is_overdue_columns')"))
    conn.commit()
    print('Version updated successfully')

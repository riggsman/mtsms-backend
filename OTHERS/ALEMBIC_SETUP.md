# Alembic Setup Guide

Alembic has been configured for database migrations in this project.

## Configuration

- **Alembic Config**: `alembic.ini`
- **Migration Scripts**: `alembic/env.py`
- **Migration Files**: `alembic/versions/`

## Database Architecture

This project uses two SQLAlchemy Base classes:
- **DefaultBase**: For global database models (tenants, system_config)
- **BaseModel_Base**: For tenant/shared database models (users, students, courses, etc.)

Alembic is configured to handle both bases by combining their metadata.

## Usage

### Check Current Migration Status
```bash
cd "E:\PERSONAL\PERSONAL WORK\MTSMS"
alembic current
```

### View Migration History
```bash
alembic history
```

### Create a New Migration (Auto-generate)
```bash
alembic revision --autogenerate -m "description of changes"
```

### Create a New Migration (Manual)
```bash
alembic revision -m "description of changes"
```

### Apply Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply migrations up to a specific revision
alembic upgrade <revision>
```

### Rollback Migrations
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision>

# Rollback all migrations
alembic downgrade base
```

### Show SQL for a Migration (without applying)
```bash
alembic upgrade head --sql
```

## Important Notes

1. **Database URL**: The database URL is automatically read from `app.conf.config.settings.DATABASE_URL`

2. **Model Imports**: All models must be imported in `alembic/env.py` for autogenerate to work properly. When adding new models, remember to import them in `env.py`.

3. **Multiple Bases**: The setup combines metadata from both `DefaultBase` and `BaseModel_Base` to detect all tables.

4. **First Migration**: The initial migration for `must_change_password` field has been created. Review it before applying.

## Reviewing Migrations

Always review auto-generated migrations before applying them:
1. Check that the changes are correct
2. Ensure no unintended changes are included
3. Test the migration on a development database first

## Example Workflow

1. Make changes to a model (e.g., add a new field)
2. Create migration: `alembic revision --autogenerate -m "add new field to model"`
3. Review the generated migration file
4. Apply migration: `alembic upgrade head`
5. Test the application

## Troubleshooting

If you encounter issues:

1. **Import Errors**: Make sure all models are imported in `alembic/env.py`
2. **Missing Tables**: Check that models are properly registered with their Base classes
3. **Database Connection**: Verify `DATABASE_URL` in your `.env` file or `app.conf.config`

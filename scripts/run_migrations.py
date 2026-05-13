"""
Script to run Alembic migrations or custom SQL migrations
Usage: 
    python scripts/run_migrations.py [upgrade|downgrade|current|history|revision]
    python scripts/run_migrations.py custom <migration_file>
"""
import sys
import os
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_alembic_command(command):
    """Run an alembic command"""
    try:
        result = subprocess.run(
            ['python', '-m', 'alembic'] + command.split(),
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running alembic command: {e}", file=sys.stderr)
        return False

def run_custom_migration(migration_file):
    """Run a custom migration from the migrations directory"""
    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'migrations'
    )
    migration_path = os.path.join(migrations_dir, migration_file)
    
    if not os.path.exists(migration_path):
        print(f"Migration file not found: {migration_path}")
        return False
    
    try:
        # Import and run the migration
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'run_migration'):
            module.run_migration()
        else:
            print("Migration module must have a run_migration() function")
            return False
        
        return True
    except Exception as e:
        print(f"Error running migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Alembic: python scripts/run_migrations.py [upgrade|downgrade|current|history|revision]")
        print("  Custom:  python scripts/run_migrations.py custom <migration_file>")
        print("\nExamples:")
        print("  python scripts/run_migrations.py upgrade head")
        print("  python scripts/run_migrations.py current")
        print("  python scripts/run_migrations.py history")
        print("  python scripts/run_migrations.py revision --autogenerate -m 'description'")
        print("  python scripts/run_migrations.py custom add_cache_version_column.py")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'custom':
        if len(sys.argv) < 3:
            print("Usage: python scripts/run_migrations.py custom <migration_file>")
            sys.exit(1)
        success = run_custom_migration(sys.argv[2])
        sys.exit(0 if success else 1)
    else:
        command_args = ' '.join(sys.argv[1:])
        success = run_alembic_command(command_args)
        sys.exit(0 if success else 1)

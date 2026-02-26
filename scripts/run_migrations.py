"""
Script to run Alembic migrations
Usage: python scripts/run_migrations.py [upgrade|downgrade|current|history]
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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_migrations.py [upgrade|downgrade|current|history|revision]")
        print("\nExamples:")
        print("  python scripts/run_migrations.py upgrade head")
        print("  python scripts/run_migrations.py current")
        print("  python scripts/run_migrations.py history")
        print("  python scripts/run_migrations.py revision --autogenerate -m 'description'")
        sys.exit(1)
    
    command = ' '.join(sys.argv[1:])
    success = run_alembic_command(command)
    sys.exit(0 if success else 1)

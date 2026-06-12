"""Test database connection."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root.parent))  # Add parent to import backend

from sqlalchemy import text

from backend.app.db import (
    timescale_engine,
    sqlite_engine,
    check_all_health,
    init_all_databases,
)

def test_connections():
    """Test both database connections."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    # Test TimescaleDB
    print("\n[1] Testing TimescaleDB connection...")
    try:
        with timescale_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            print("    [OK] TimescaleDB connection successful")
    except Exception as e:
        print(f"    [FAIL] TimescaleDB connection failed: {e}")
        return False
    
    # Test SQLite
    print("\n[2] Testing SQLite connection...")
    try:
        with sqlite_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            print("    [OK] SQLite connection successful")
    except Exception as e:
        print(f"    [FAIL] SQLite connection failed: {e}")
        return False
    
    # Test health check
    print("\n[3] Testing health check...")
    health = check_all_health()
    print(f"    TimescaleDB: {'OK healthy' if health['timescale'] else 'FAIL unhealthy'}")
    print(f"    SQLite: {'OK healthy' if health['sqlite'] else 'FAIL unhealthy'}")
    
    if not all(health.values()):
        return False
    
    # Initialize databases
    print("\n[4] Initializing databases...")
    try:
        init_all_databases()
        print("    [OK] Databases initialized")
    except Exception as e:
        print(f"    [FAIL] Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_connections()
    sys.exit(0 if success else 1)

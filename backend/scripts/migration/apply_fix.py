"""Apply database migration to fix missing fields in SQLite"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from quant_engine.core.models.evolution import Base

# SQLite database path
SQLITE_PATH = os.getenv(
    "SQLITE_PATH",
    os.path.join(backend_dir, "data", "runtime.db")
)

def apply_migration():
    """Apply the migration to add missing fields to SQLite"""
    engine = create_engine(f"sqlite:///{SQLITE_PATH}", connect_args={"check_same_thread": False})
    
    # First, create all tables if they don't exist
    print("Creating all tables in SQLite...")
    Base.metadata.create_all(bind=engine)
    print("Tables created/verified.")
    
    with engine.connect() as conn:
        # Add IC fields to evolution_factors (SQLite syntax)
        print("Adding IC fields to evolution_factors...")
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN ic_mean_4h FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN ic_mean_24h FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN ic_mean_168h FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN ic_std FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN ic_ir FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN ic_half_life INTEGER"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN factor_category VARCHAR(32)"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN is_selected_strategy BOOLEAN DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE evolution_factors ADD COLUMN strategy_rank INTEGER"))
        except Exception:
            pass
        
        # Add IC fields to validation_pipeline_data
        print("Adding IC fields to validation_pipeline_data...")
        try:
            conn.execute(text("ALTER TABLE validation_pipeline_data ADD COLUMN ic_input INTEGER DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE validation_pipeline_data ADD COLUMN ic_output INTEGER DEFAULT 0"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE validation_pipeline_data ADD COLUMN ic_drop INTEGER DEFAULT 0"))
        except Exception:
            pass
        
        # Add IC fields to candidates
        print("Adding IC fields to candidates...")
        try:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN ic_mean_4h FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN ic_mean_24h FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN ic_mean_168h FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN ic_std FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN ic_ir FLOAT"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE candidates ADD COLUMN ic_half_life INTEGER"))
        except Exception:
            pass
        
        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    apply_migration()

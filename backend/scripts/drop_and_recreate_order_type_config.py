"""
Drop and recreate tables with correct schema for datetime fields
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import engine
from sqlalchemy import text

def drop_and_recreate():
    """Drop and recreate tables with correct schema"""
    with engine.connect() as conn:
        # Drop the tables
        conn.execute(text("DROP TABLE IF EXISTS order_type_config CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS risk_config CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS position_limit_config CASCADE"))
        conn.commit()
        print("✓ Dropped tables")
        
        # Recreate order_type_config
        conn.execute(text("""
            CREATE TABLE order_type_config (
                id SERIAL PRIMARY KEY,
                order_type VARCHAR(32) UNIQUE NOT NULL,
                description TEXT,
                is_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        conn.commit()
        print("✓ Recreated order_type_config table")
        
        # Recreate risk_config
        conn.execute(text("""
            CREATE TABLE risk_config (
                id SERIAL PRIMARY KEY,
                config_type VARCHAR(16) NOT NULL,
                symbol VARCHAR(16),
                max_total_margin_ratio FLOAT NOT NULL,
                daily_max_loss_ratio FLOAT NOT NULL,
                max_drawdown_ratio FLOAT NOT NULL,
                updated_by VARCHAR(32) NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                notes TEXT,
                CONSTRAINT uq_risk_config_type_symbol UNIQUE (config_type, symbol)
            )
        """))
        conn.commit()
        print("✓ Recreated risk_config table")
        
        # Recreate position_limit_config
        conn.execute(text("""
            CREATE TABLE position_limit_config (
                id SERIAL PRIMARY KEY,
                config_type VARCHAR(16) NOT NULL,
                symbol VARCHAR(16),
                max_position_ratio FLOAT NOT NULL,
                max_total_margin_ratio FLOAT NOT NULL,
                updated_by VARCHAR(32) NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                notes TEXT,
                CONSTRAINT uq_position_limit_config_type_symbol UNIQUE (config_type, symbol)
            )
        """))
        conn.commit()
        print("✓ Recreated position_limit_config table")

if __name__ == "__main__":
    drop_and_recreate()

#!/usr/bin/env python3
"""
Database initialization script - PostgreSQL only.

1. Creates all tables in PostgreSQL
2. Creates hypertables for timeseries data
3. Seeds symbol configurations into symbol_switches table
"""

import asyncio
import os
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Base, SymbolSwitch, SymbolMode

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/quant_db",
)

# 12 symbols with grouping and margin estimates
SYMBOLS = [
    # A组 - 化工能源
    {"symbol": "MA", "group": "A", "margin": 3000, "name": "甲醇"},
    {"symbol": "TA", "group": "A", "margin": 3500, "name": "PTA"},
    {"symbol": "SA", "group": "A", "margin": 4000, "name": "纯碱"},
    {"symbol": "PP", "group": "A", "margin": 4000, "name": "聚丙烯"},
    {"symbol": "SC", "group": "A", "margin": 55000, "name": "原油"},
    # B组 - 黑色建材
    {"symbol": "RB", "group": "B", "margin": 4000, "name": "螺纹钢"},
    {"symbol": "FG", "group": "B", "margin": 4000, "name": "玻璃"},
    # C组 - 农产品
    {"symbol": "M", "group": "C", "margin": 3500, "name": "豆粕"},
    {"symbol": "SR", "group": "C", "margin": 4500, "name": "白糖"},
    # D组 - 贵金属金融
    {"symbol": "AU", "group": "D", "margin": 65000, "name": "黄金"},
    {"symbol": "CU", "group": "D", "margin": 45000, "name": "铜"},
    {"symbol": "IF", "group": "D", "margin": 140000, "name": "股指"},
]


# ---------------------------------------------------------------------------
# PostgreSQL initialization
# ---------------------------------------------------------------------------

async def init_database() -> None:
    """Initialize PostgreSQL database."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("[DB] All tables created")

        # Convert to hypertables if not already
        hypertables = [
            ("ohlcv_1h", "ts"),
            ("ohlcv_1d", "ts"),
            ("factor_values", "ts"),
        ]
        for table, time_col in hypertables:
            try:
                result = await conn.execute(text(
                    f"SELECT hypertable_name FROM timescaledb_information.hypertables "
                    f"WHERE hypertable_name = '{table}'"
                ))
                if result.fetchone() is None:
                    await conn.execute(
                        text(
                            f"SELECT create_hypertable('{table}', '{time_col}', "
                            f"if_not_exists => TRUE);"
                        )
                    )
                    print(f"[DB] Hypertable created: {table}")
                else:
                    print(f"[DB] Hypertable already exists: {table}")
            except Exception as e:
                print(f"[DB] Hypertable check/creation for {table} error: {e}")

    # Seed symbol configurations
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        existing = await session.execute(text("SELECT symbol FROM symbol_switches"))
        existing_symbols = {row[0] for row in existing.fetchall()}

        new_count = 0
        for sym in SYMBOLS:
            if sym["symbol"] in existing_symbols:
                continue
            switch = SymbolSwitch(
                symbol=sym["symbol"],
                mode=SymbolMode.OFF,
                group_name=sym["group"],
                margin_per_lot=sym["margin"],
                max_lots=1,
                is_priority=sym["margin"] <= 5000,
            )
            session.add(switch)
            new_count += 1

        await session.commit()
        if new_count > 0:
            print(f"[DB] Seeded {new_count} symbol configurations")
        else:
            print(f"[DB] Symbol configurations already exist")

    await engine.dispose()
    print("[DB] Initialization complete!")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=" * 60)
    print("Quant Auto-Evolution Factor Mining System - DB Init (PostgreSQL only)")
    print("=" * 60)
    await init_database()
    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

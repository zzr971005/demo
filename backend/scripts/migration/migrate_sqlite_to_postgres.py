"""
SQLite -> PostgreSQL 数据迁移脚本

将SQLite中的业务数据迁移到PostgreSQL，包括：
- candidates（候选策略）
- trades（交易记录）
- evolution_generations（进化世代）
- risk_events（风控事件）
- symbol_switches（品种开关）
"""

import os
import sqlite3
import logging
from datetime import datetime

import psycopg2
from psycopg2 import sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置
SQLITE_PATH = os.getenv("SQLITE_PATH", "data/runtime.db")
PG_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/quant_db")

def parse_pg_url(url):
    """解析PostgreSQL连接URL"""
    from urllib.parse import urlparse
    parsed = urlparse(url.replace("postgresql+psycopg2://", "postgres://"))
    return {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432
    }

def connect_sqlite(path):
    """连接SQLite"""
    return sqlite3.connect(path)

def connect_postgres(url):
    """连接PostgreSQL"""
    config = parse_pg_url(url)
    return psycopg2.connect(**config)

def migrate_table(sqlite_conn, pg_conn, table_name, columns):
    """迁移单个表"""
    cursor_sqlite = sqlite_conn.cursor()
    cursor_pg = pg_conn.cursor()
    
    # 获取SQLite数据
    cursor_sqlite.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
    rows = cursor_sqlite.fetchall()
    
    if not rows:
        logger.info(f"表 {table_name} 为空，跳过")
        return 0
    
    # 构建INSERT语句
    placeholders = ', '.join(['%s'] * len(columns))
    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(', ').join(map(sql.Identifier, columns)),
        sql.SQL(placeholders)
    )
    
    # 批量插入
    try:
        cursor_pg.executemany(insert_query, rows)
        pg_conn.commit()
        logger.info(f"成功迁移 {table_name}: {len(rows)} 条记录")
        return len(rows)
    except Exception as e:
        logger.error(f"迁移 {table_name} 失败: {e}")
        raise

def main():
    logger.info("=== 开始SQLite -> PostgreSQL数据迁移 ===")
    
    # 连接数据库
    logger.info(f"连接SQLite: {SQLITE_PATH}")
    sqlite_conn = connect_sqlite(SQLITE_PATH)
    
    logger.info(f"连接PostgreSQL: {PG_URL}")
    pg_conn = connect_postgres(PG_URL)
    
    try:
        # 迁移表定义
        tables = {
            "candidates": [
                "id", "symbol", "status", "regime", "formula", "params",
                "parent_id", "generation", "sharpe_train", "sharpe_val",
                "sharpe_test", "sharpe_paper_5d", "max_drawdown", "calmar",
                "win_rate", "profit_factor", "total_trades", "avg_holding_bars",
                "is_seed", "seed_code", "deployed_at", "degraded_at",
                "retired_at", "retire_reason", "is_active", "created_at", "updated_at"
            ],
            "trades": [
                "id", "symbol", "candidate_id", "direction", "offset",
                "open_time", "close_time", "open_price", "close_price",
                "volume", "pnl", "fee", "status", "created_at", "updated_at"
            ],
            "evolution_generations": [
                "id", "symbol", "generation", "stage", "timestamp",
                "population_size", "new_candidates", "pruned_candidates",
                "best_fitness", "best_sharpe", "avg_fitness", "avg_sharpe",
                "diversity", "created_at"
            ],
            "risk_events": [
                "id", "symbol", "event_type", "level", "message",
                "triggered_at", "resolved_at", "is_resolved", "created_at"
            ],
            "symbol_switches": [
                "id", "symbol", "status", "config", "updated_at"
            ]
        }
        
        total_migrated = 0
        for table_name, columns in tables.items():
            count = migrate_table(sqlite_conn, pg_conn, table_name, columns)
            total_migrated += count
        
        logger.info(f"=== 迁移完成！共迁移 {total_migrated} 条记录 ===")
        
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()

"""
SQLite数据库迁移脚本：为 evolution_factors 表添加IC相关字段
迁移版本: v1 -> v2
"""

import os
import sqlite3
import logging

# SQLite数据库路径（与evolution.py中定义一致）
# 从 backend/scripts/migration/ 向上4级到项目根目录，然后进入 data/runtime.db
SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "runtime.db"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """执行迁移"""
    db_path = os.path.abspath(SQLITE_PATH)
    logger.info(f"SQLite数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查现有字段
        cursor.execute("PRAGMA table_info(evolution_factors)")
        columns = cursor.fetchall()
        existing_fields = {col[1] for col in columns}
        logger.info(f"现有字段: {existing_fields}")
        
        # 需要添加的IC相关字段
        new_fields = {
            "ic_mean_4h": "REAL",
            "ic_mean_24h": "REAL",
            "ic_mean_168h": "REAL",
            "ic_std": "REAL",
            "ic_ir": "REAL",
            "ic_half_life": "INTEGER",
            "factor_category": "VARCHAR(32)",
            "is_selected_strategy": "BOOLEAN DEFAULT 0",
            "strategy_rank": "INTEGER",
        }
        
        # 添加缺失的字段
        for field, field_type in new_fields.items():
            if field not in existing_fields:
                logger.info(f"添加字段: {field} ({field_type})")
                cursor.execute(f"ALTER TABLE evolution_factors ADD COLUMN {field} {field_type}")
                conn.commit()
            else:
                logger.info(f"字段已存在: {field}")
        
        logger.info("迁移完成!")
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

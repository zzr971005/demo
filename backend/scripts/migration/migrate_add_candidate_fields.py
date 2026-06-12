"""
数据库迁移脚本：为 candidates 表添加新字段
迁移版本: v2 -> v3
"""

import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """执行迁移"""
    # 连接到 PostgreSQL (使用 psycopg2 驱动)
    db_url = os.getenv("DATABASE_URL", "postgresql://quant_user:quant_pass@localhost:5432/quant_db")
    db_url = db_url.replace("+psycopg2", "").replace("+pg8000", "")
    if not db_url.startswith("postgresql://"):
        db_url = "postgresql+psycopg2" + db_url[db_url.find(":"):]
    else:
        db_url = "postgresql+psycopg2" + db_url[len("postgresql"):]
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # 检查现有字段
        inspector = inspect(engine)
        columns = inspector.get_columns("candidates")
        existing_fields = {col["name"] for col in columns}
        logger.info(f"现有字段: {existing_fields}")
        
        # 需要添加的字段
        new_fields = {
            "total_return": "NUMERIC(20, 6)",
            "node_count": "INTEGER",
            "tree_depth": "INTEGER",
            "pbo": "NUMERIC(10, 6)",
            "dsr": "NUMERIC(10, 6)",
            "wfe": "NUMERIC(10, 6)",
        }
        
        # 添加缺失的字段
        for field, field_type in new_fields.items():
            if field not in existing_fields:
                logger.info(f"添加字段: {field} ({field_type})")
                conn.execute(text(f"ALTER TABLE candidates ADD COLUMN {field} {field_type}"))
                conn.commit()
            else:
                logger.info(f"字段已存在: {field}")
        
        logger.info("迁移完成!")


if __name__ == "__main__":
    migrate()

"""
数据库迁移脚本：添加真实数据表
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import engine, init_db
from app.models import Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """执行数据库迁移"""
    logger.info("开始数据库迁移：添加真实数据表...")
    
    try:
        # 创建所有新表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
        
        # 验证新表是否创建成功
        new_tables = [
            "simulation_orders",
            "simulation_positions",
            "simulation_sessions",
            "risk_config",
            "strategy_weights",
            "capital_allocation",
            "portfolio_metrics",
            "order_type_config",
            "liquidity_risk_analysis",
            "correlation_matrices",
            "backtest_live_comparisons",
            "generated_reports",
            "ab_test_results",
            "arbitrage_opportunities",
            "strategy_monitor_status",
            "live_transition_candidates",
            "replay_sessions",
            "portfolio_optimizations",
        ]
        
        with engine.connect() as conn:
            for table in new_tables:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = '{table}'
                    );
                """))
                exists = result.fetchone()[0]
                if exists:
                    logger.info(f"✓ 表 {table} 已创建")
                else:
                    logger.warning(f"✗ 表 {table} 未创建")
        
        logger.info("数据库迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

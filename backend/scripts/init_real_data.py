"""
数据初始化脚本：插入默认配置数据
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import get_session
from app.models import (
    RiskConfig, PositionLimitConfig, OrderTypeConfig,
    StrategyWeight, CapitalAllocation
)
from sqlalchemy import text, select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_default_configs():
    """初始化默认配置"""
    logger.info("开始初始化默认配置数据...")
    
    try:
        with get_session() as session:
            # 检查是否已存在默认风控配置
            existing_risk = session.execute(
                select(RiskConfig).where(RiskConfig.config_type == "global").limit(1)
            ).scalar_one_or_none()

            if not existing_risk:
                # 插入默认风控配置
                default_risk_config = RiskConfig(
                    config_type="global",
                    max_total_margin_ratio=0.8,
                    daily_max_loss_ratio=0.05,
                    max_drawdown_ratio=0.15,
                    updated_by="system"
                )
                session.add(default_risk_config)
                logger.info("✓ 插入默认风控配置")
            else:
                logger.info("✓ 风控配置已存在，跳过")

            # 检查仓位限制配置
            existing_position = session.execute(
                select(PositionLimitConfig).where(PositionLimitConfig.config_type == "global").limit(1)
            ).scalar_one_or_none()

            if not existing_position:
                # 插入默认仓位限制配置
                default_position_limit = PositionLimitConfig(
                    config_type="global",
                    max_position_ratio=0.3,
                    max_total_margin_ratio=0.8,
                    updated_by="system"
                )
                session.add(default_position_limit)
                logger.info("✓ 插入默认仓位限制配置")
            else:
                logger.info("✓ 仓位限制配置已存在，跳过")

            # 检查订单类型配置
            existing_order_types = session.execute(
                select(OrderTypeConfig)
            ).scalars().all()

            if len(existing_order_types) == 0:
                # 插入默认订单类型配置
                order_types = [
                    OrderTypeConfig(order_type="MARKET", description="市价单", is_enabled=True),
                    OrderTypeConfig(order_type="LIMIT", description="限价单", is_enabled=True),
                    OrderTypeConfig(order_type="STOP", description="止损单", is_enabled=True),
                    OrderTypeConfig(order_type="STOP_LIMIT", description="止损限价单", is_enabled=True),
                ]
                session.add_all(order_types)
                logger.info("✓ 插入默认订单类型配置")
            else:
                logger.info("✓ 订单类型配置已存在，跳过")

            session.commit()
            logger.info("默认配置数据初始化完成")
            return True
            
    except Exception as e:
        logger.error(f"默认配置数据初始化失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = init_default_configs()
    sys.exit(0 if success else 1)

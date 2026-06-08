"""
市场微观结构API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select

from app.db import get_session
from app.models import MicrostructureData
from quant_engine.ops.tqsdk_trading import get_trading_engine, TradingMode
from app.config import get_settings

router = APIRouter(prefix="/api/microstructure", tags=["microstructure"])


@router.get("/analysis/{symbol}")
async def get_microstructure_analysis(symbol: str) -> Dict[str, Any]:
    """获取市场微观结构分析"""
    with get_session() as session:
        # Get the most recent microstructure data for this symbol
        query = select(MicrostructureData).where(
            MicrostructureData.symbol == symbol.upper()
        ).order_by(MicrostructureData.timestamp.desc()).limit(1)
        result = session.execute(query)
        data = result.scalar_one_or_none()
        
        if data:
            return {
                "symbol": symbol,
                "bid_ask_spread": data.bid_ask_spread,
                "order_flow": data.order_flow,
                "depth_imbalance": data.depth_imbalance,
                "volume": data.volume,
                "vwap": data.vwap,
                "timestamp": data.timestamp.isoformat(),
                "has_data": True,
            }
        else:
            # 无微观结构数据时返回 null（不伪造数值）
            return {
                "symbol": symbol,
                "bid_ask_spread": None,
                "order_flow": None,
                "depth_imbalance": None,
                "volume": None,
                "vwap": None,
                "timestamp": None,
                "has_data": False,
            }


@router.get("/liquidity/{symbol}")
async def get_liquidity_metrics(symbol: str) -> Dict[str, Any]:
    """获取流动性指标"""
    config = get_settings()
    
    # Get trading engine for market data
    engine = get_trading_engine()
    
    # Connect to TQSDK if not connected
    if not engine.connected:
        engine.connect(
            mode=TradingMode.PAPER,
            account_id=config.tqsdk_account,
            password=config.tqsdk_password
        )
    
    # Get quote from TQSDK
    quote = engine.get_quote(symbol.upper())
    volume = quote.get("volume", 0) if quote else 0
    
    with get_session() as session:
        # Get the most recent microstructure data for this symbol
        query = select(MicrostructureData).where(
            MicrostructureData.symbol == symbol.upper()
        ).order_by(MicrostructureData.timestamp.desc()).limit(1)
        result = session.execute(query)
        data = result.scalar_one_or_none()
        
        if data:
            # Calculate spread ratio from bid-ask spread
            spread_ratio = data.bid_ask_spread if data.bid_ask_spread else 0.0
            
            return {
                "symbol": symbol,
                "volume": volume,
                "spread_ratio": spread_ratio,
                "order_flow": data.order_flow,
                "depth_imbalance": data.depth_imbalance,
            }
        else:
            return {
                "symbol": symbol,
                "volume": volume,
                "spread_ratio": 0.0,
                "liquidity_score": 0.0
            }

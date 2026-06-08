"""
流动性风险API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import select

from app.db import get_session
from app.models import LiquidityRiskAnalysis
from quant_engine.ops.tqsdk_trading import get_trading_engine, TradingMode
from app.config import get_settings

router = APIRouter(prefix="/api/liquidity-risk", tags=["liquidity-risk"])


@router.get("/analysis/{symbol}")
async def get_liquidity_risk_analysis(symbol: str) -> Dict[str, Any]:
    """获取流动性风险分析"""
    with get_session() as session:
        # Get the most recent liquidity risk analysis for this symbol
        query = select(LiquidityRiskAnalysis).where(
            LiquidityRiskAnalysis.symbol == symbol.upper()
        ).order_by(LiquidityRiskAnalysis.analysis_date.desc()).limit(1)
        result = session.execute(query)
        analysis = result.scalar_one_or_none()
        
        if analysis:
            return {
                "symbol": symbol,
                "liquidity_ratio": analysis.liquidity_ratio,
                "amihud_illiquidity": analysis.amihud_illiquidity,
                "risk_score": analysis.risk_score,
                "analysis_date": analysis.analysis_date.isoformat(),
            }
        else:
            return {
                "symbol": symbol,
                "liquidity_ratio": 1.0,
                "amihud_illiquidity": 0.0,
                "risk_score": 0.0
            }


@router.post("/check-order")
async def check_liquidity_for_order(
    symbol: str,
    volume: float
) -> Dict[str, Any]:
    """检查订单流动性"""
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
    
    if not quote:
        return {
            "passes": False,
            "message": "无法获取市场数据"
        }
    
    # Get current volume and check if order volume is reasonable
    current_volume = quote.get("volume", 0)
    last_price = quote.get("last_price", 0)
    
    # Calculate liquidity metrics
    # Rule: Order volume should not exceed 10% of daily volume
    volume_ratio = volume / current_volume if current_volume > 0 else 1.0
    
    # Rule: Order value should be reasonable relative to price
    order_value = volume * last_price
    
    # Get liquidity risk analysis from database
    with get_session() as session:
        query = select(LiquidityRiskAnalysis).where(
            LiquidityRiskAnalysis.symbol == symbol.upper()
        ).order_by(LiquidityRiskAnalysis.analysis_date.desc()).limit(1)
        result = session.execute(query)
        analysis = result.scalar_one_or_none()
        
        risk_score = analysis.risk_score if analysis else 0.0
        liquidity_ratio = analysis.liquidity_ratio if analysis else 1.0
    
    # Determine if order passes liquidity check
    passes = True
    message = "流动性检查通过"
    
    if volume_ratio > 0.1:
        passes = False
        message = f"订单量过大，超过日成交量的10% ({volume_ratio:.1%})"
    elif risk_score > 0.7:
        passes = False
        message = f"流动性风险过高 (风险评分: {risk_score:.2f})"
    elif liquidity_ratio < 0.5:
        passes = False
        message = f"流动性比率过低 ({liquidity_ratio:.2f})"
    
    return {
        "passes": passes,
        "message": message,
        "volume_ratio": volume_ratio,
        "risk_score": risk_score,
        "liquidity_ratio": liquidity_ratio
    }

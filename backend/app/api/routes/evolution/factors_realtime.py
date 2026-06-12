"""
实时因子API

提供实时因子值查询和管理
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime

from quant_engine.ops.realtime_factor_engine import (
    get_factor_engine,
    RealtimeFactorEngine,
    FactorValue,
)

logger = logging.getLogger("quant_engine.api.factors_realtime")

router = APIRouter(prefix="/factors-realtime", tags=["factors_realtime"])


# ============ 数据模型 ============

class FactorValueResponse(BaseModel):
    """因子值响应"""
    factor_id: str
    symbol: str
    timestamp: datetime
    value: float
    raw_value: float
    mean_20d: float
    std_20d: float
    zscore: float
    rank: int
    
    class Config:
        from_attributes = True


class RegisterFactorRequest(BaseModel):
    """注册因子请求"""
    factor_id: str
    expression: str
    symbol: str


class RegisterFactorResponse(BaseModel):
    """注册因子响应"""
    success: bool
    message: str
    factor_id: str


class FactorListResponse(BaseModel):
    """因子列表响应"""
    factor_id: str
    expression: str
    symbol: str
    current_value: Optional[float] = None
    zscore: Optional[float] = None


# ============ 依赖注入 ============

def get_factor_engine_instance() -> RealtimeFactorEngine:
    """获取因子引擎实例"""
    engine = get_factor_engine()
    
    # 确保引擎已启动
    if not engine._running:
        engine.start()
    
    return engine


# ============ API端点 ============

@router.post(
    "/register",
    response_model=RegisterFactorResponse,
    summary="注册因子",
    description="注册一个因子到实时计算引擎",
)
async def register_factor(
    request: RegisterFactorRequest,
    engine: RealtimeFactorEngine = Depends(get_factor_engine_instance),
) -> RegisterFactorResponse:
    """注册因子"""
    try:
        success = engine.register_factor(
            factor_id=request.factor_id,
            expression=request.expression,
            symbol=request.symbol,
        )
        
        if success:
            return RegisterFactorResponse(
                success=True,
                message=f"Factor {request.factor_id} registered successfully",
                factor_id=request.factor_id,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to register factor {request.factor_id}"
            )
            
    except Exception as e:
        logger.error(f"Error registering factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/unregister/{factor_id}",
    response_model=RegisterFactorResponse,
    summary="注销因子",
    description="从实时计算引擎注销一个因子",
)
async def unregister_factor(
    factor_id: str,
    engine: RealtimeFactorEngine = Depends(get_factor_engine_instance),
) -> RegisterFactorResponse:
    """注销因子"""
    try:
        engine.unregister_factor(factor_id)
        
        return RegisterFactorResponse(
            success=True,
            message=f"Factor {factor_id} unregistered successfully",
            factor_id=factor_id,
        )
        
    except Exception as e:
        logger.error(f"Error unregistering factor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/value/{factor_id}",
    response_model=Optional[FactorValueResponse],
    summary="获取因子值",
    description="获取指定因子的最新计算值",
)
async def get_factor_value(
    factor_id: str,
    engine: RealtimeFactorEngine = Depends(get_factor_engine_instance),
) -> Optional[FactorValueResponse]:
    """获取因子值"""
    try:
        value = engine.get_factor_value(factor_id)
        
        if value is None:
            return None
        
        return FactorValueResponse(
            factor_id=value.factor_id,
            symbol=value.symbol,
            timestamp=value.timestamp,
            value=value.value,
            raw_value=value.raw_value,
            mean_20d=value.mean_20d,
            std_20d=value.std_20d,
            zscore=value.zscore,
            rank=value.rank,
        )
        
    except Exception as e:
        logger.error(f"Error getting factor value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/values",
    response_model=List[FactorValueResponse],
    summary="获取所有因子值",
    description="获取所有注册因子的最新计算值",
)
async def get_all_factor_values(
    engine: RealtimeFactorEngine = Depends(get_factor_engine_instance),
) -> List[FactorValueResponse]:
    """获取所有因子值"""
    try:
        values = engine.get_all_factor_values()
        
        return [
            FactorValueResponse(
                factor_id=v.factor_id,
                symbol=v.symbol,
                timestamp=v.timestamp,
                value=v.value,
                raw_value=v.raw_value,
                mean_20d=v.mean_20d,
                std_20d=v.std_20d,
                zscore=v.zscore,
                rank=v.rank,
            )
            for v in values.values()
        ]
        
    except Exception as e:
        logger.error(f"Error getting all factor values: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/values/{symbol}",
    response_model=List[FactorValueResponse],
    summary="获取品种因子值",
    description="获取指定品种的所有因子值",
)
async def get_factor_values_by_symbol(
    symbol: str,
    engine: RealtimeFactorEngine = Depends(get_factor_engine_instance),
) -> List[FactorValueResponse]:
    """获取指定品种的因子值"""
    try:
        values = engine.get_factor_values_by_symbol(symbol)
        
        return [
            FactorValueResponse(
                factor_id=v.factor_id,
                symbol=v.symbol,
                timestamp=v.timestamp,
                value=v.value,
                raw_value=v.raw_value,
                mean_20d=v.mean_20d,
                std_20d=v.std_20d,
                zscore=v.zscore,
                rank=v.rank,
            )
            for v in values
        ]
        
    except Exception as e:
        logger.error(f"Error getting factor values by symbol: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/list",
    response_model=List[FactorListResponse],
    summary="获取因子列表",
    description="获取所有已注册因子的列表",
)
async def get_factor_list(
    engine: RealtimeFactorEngine = Depends(get_factor_engine_instance),
) -> List[FactorListResponse]:
    """获取因子列表"""
    try:
        calculators = engine.calculators
        factor_values = engine.factor_values
        
        result = []
        for factor_id, calculator in calculators.items():
            value = factor_values.get(factor_id)
            result.append(FactorListResponse(
                factor_id=factor_id,
                expression=calculator.expression,
                symbol=calculator.symbol,
                current_value=value.value if value else None,
                zscore=value.zscore if value else None,
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting factor list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ WebSocket ============

@router.websocket("/ws")
async def factor_websocket(
    websocket: WebSocket,
    engine: RealtimeFactorEngine = Depends(get_factor_engine_instance),
):
    """WebSocket实时因子推送"""
    await websocket.accept()
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to factor value stream"
        })
        
        # 设置回调函数
        def on_factor_update(value: FactorValue):
            import asyncio
            try:
                asyncio.create_task(websocket.send_json({
                    "type": "factor_update",
                    "data": {
                        "factor_id": value.factor_id,
                        "symbol": value.symbol,
                        "timestamp": value.timestamp.isoformat(),
                        "value": value.value,
                        "raw_value": value.raw_value,
                        "zscore": value.zscore,
                    }
                }))
            except Exception:
                pass
        
        # 添加回调
        engine.add_callback(on_factor_update)
        
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_json()
                
                if data.get("action") == "register":
                    factor_id = data.get("factor_id")
                    expression = data.get("expression")
                    symbol = data.get("symbol")
                    
                    if factor_id and expression and symbol:
                        engine.register_factor(factor_id, expression, symbol)
                        await websocket.send_json({
                            "type": "registered",
                            "factor_id": factor_id
                        })
                
                elif data.get("action") == "unregister":
                    factor_id = data.get("factor_id")
                    if factor_id:
                        engine.unregister_factor(factor_id)
                        await websocket.send_json({
                            "type": "unregistered",
                            "factor_id": factor_id
                        })
                        
        except WebSocketDisconnect:
            pass
        finally:
            engine.remove_callback(on_factor_update)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

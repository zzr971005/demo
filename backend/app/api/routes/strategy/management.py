"""
策略管理API

提供：
- 因子池查询
- 策略选择
- 策略轮换
- 轮换历史查询
- 因子衰减历史查询
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db import get_session
from quant_engine.ops.strategy_selector import StrategySelector
from quant_engine.ops.strategy_rotation import StrategyRotator, get_current_strategies, get_top_factors
from quant_engine.core.models.evolution import FactorDecayHistory, StrategyRotationHistory
import yaml

router = APIRouter(prefix="/api/strategy-management", tags=["strategy-management"])


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class FactorInfo(BaseModel):
    id: str
    symbol: str
    formula: str
    sharpe_train: Optional[float]
    sharpe_test: Optional[float]
    calmar: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    total_trades: Optional[int]
    ic_mean_4h: Optional[float]
    ic_mean_24h: Optional[float]
    ic_mean_168h: Optional[float]
    ic_std: Optional[float]
    ic_ir: Optional[float]
    ic_half_life: Optional[int]
    factor_category: Optional[str]
    strategy_rank: Optional[int]


class StrategySelectionRequest(BaseModel):
    symbol: str
    count: int = 5


class StrategyRotationRequest(BaseModel):
    symbol: str


class RotationHistoryItem(BaseModel):
    id: int
    symbol: str
    old_factor_id: Optional[str]
    new_factor_id: str
    rotation_reason: Optional[str]
    score_improvement: Optional[float]
    rotated_at: str


class DecayHistoryItem(BaseModel):
    id: int
    factor_id: str
    symbol: str
    ic_value: float
    ic_window: int
    recorded_at: str


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def get_factor_pool_config():
    """从数据库加载因子池配置"""
    try:
        from app.db import get_session
        from app.models import Config
        
        with get_session() as session:
            # Try to load config from database
            query = select(Config).where(Config.key == "factor_pool_config")
            result = session.execute(query)
            config = result.scalar_one_or_none()
            
            if config and config.value:
                import json
                return json.loads(config.value)
        
        # Return default configuration if not found in database
        return {
            "max_strategies": 5,
            "min_ic": 0.02,
            "max_correlation": 0.7,
            "selection_method": "ic_weighted",
        }
    except Exception as e:
        logger.error(f"加载因子池配置失败: {e}")
        return {
            "max_strategies": 5,
            "min_ic": 0.02,
            "max_correlation": 0.7,
            "selection_method": "ic_weighted",
        }


# ---------------------------------------------------------------------------
# API端点
# ---------------------------------------------------------------------------

@router.get("/pool/{symbol}")
async def get_factor_pool(
    symbol: str,
    limit: int = 50,
    session: Session = Depends(get_session)
) -> List[FactorInfo]:
    """
    获取因子池
    
    Parameters
    ----------
    symbol : str
        品种代码
    limit : int
        因子数量
    
    Returns
    -------
    List[FactorInfo]
        因子列表
    """
    factors = get_top_factors(session, symbol, limit)
    return [FactorInfo(**f) for f in factors]


@router.post("/strategies/select")
async def select_strategies(
    request: StrategySelectionRequest,
    session: Session = Depends(get_session)
) -> List[FactorInfo]:
    """
    选择策略
    
    Parameters
    ----------
    request : StrategySelectionRequest
        选择请求
    
    Returns
    -------
    List[FactorInfo]
        选择的策略列表
    """
    config = get_factor_pool_config()
    selector = StrategySelector(config)
    
    top_factors = get_top_factors(session, request.symbol, limit=50)
    selected = selector.select_strategies(top_factors, count=request.count)
    
    # 更新数据库标记
    from app.models import Candidate
    for i, factor in enumerate(selected):
        candidate = session.query(Candidate).filter(Candidate.id == factor["id"]).first()
        if candidate:
            candidate.is_selected_strategy = True
            candidate.strategy_rank = i + 1
    
    return [FactorInfo(**f) for f in selected]


@router.post("/strategies/rotate")
async def rotate_strategies(
    request: StrategyRotationRequest,
    session: Session = Depends(get_session)
) -> dict:
    """
    手动触发策略轮换
    
    Parameters
    ----------
    request : StrategyRotationRequest
        轮换请求
    
    Returns
    -------
    dict
        轮换结果
    """
    config = get_factor_pool_config()
    rotator = StrategyRotator(config)
    
    current_strategies = get_current_strategies(session, request.symbol)
    top_factors = get_top_factors(session, request.symbol, limit=50)
    
    new_strategies, rotation_history = rotator.execute_rotation(
        request.symbol,
        current_strategies,
        top_factors,
        session
    )
    
    return {
        "symbol": request.symbol,
        "new_strategies": [FactorInfo(**s) for s in new_strategies],
        "rotation_history": rotation_history,
        "message": f"策略轮换完成，共轮换 {len(rotation_history)} 个策略"
    }


@router.get("/rotation-history/{symbol}")
async def get_rotation_history(
    symbol: str,
    limit: int = 50,
    session: Session = Depends(get_session)
) -> List[RotationHistoryItem]:
    """
    获取轮换历史
    
    Parameters
    ----------
    symbol : str
        品种代码
    limit : int
        历史记录数量
    
    Returns
    -------
    List[RotationHistoryItem]
        轮换历史列表
    """
    history = StrategyRotationHistory.get_symbol_history(session, symbol, limit)
    return [RotationHistoryItem(**h.to_dict()) for h in history]


@router.get("/decay-history/{factor_id}")
async def get_decay_history(
    factor_id: str,
    limit: int = 100,
    session: Session = Depends(get_session)
) -> List[DecayHistoryItem]:
    """
    获取因子衰减历史
    
    Parameters
    ----------
    factor_id : str
        因子ID
    limit : int
        历史记录数量
    
    Returns
    -------
    List[DecayHistoryItem]
        衰减历史列表
    """
    history = FactorDecayHistory.get_factor_history(session, factor_id, limit)
    return [DecayHistoryItem(**h.to_dict()) for h in history]


@router.get("/strategies/current/{symbol}")
async def get_current_strategies_api(
    symbol: str,
    session: Session = Depends(get_session)
) -> List[FactorInfo]:
    """
    获取当前策略
    
    Parameters
    ----------
    symbol : str
        品种代码
    
    Returns
    -------
    List[FactorInfo]
        当前策略列表
    """
    strategies = get_current_strategies(session, symbol)
    return [FactorInfo(**s) for s in strategies]

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_db
from app.config import Settings, get_config
from app.crud import (
    get_running_candidate_by_symbol,
    get_symbol_switch,
    get_today_pnl_by_symbol,
    update_symbol_mode,
)
from app.models import SymbolMode

router = APIRouter(tags=["symbols"])


class SymbolDetailResponse(BaseModel):
    symbol: str
    name: str
    exchange: str
    group: str
    lot: int
    margin_rate: float
    max_margin: float
    evolution_pool: int
    current_margin_usage: float = 0.0
    running_strategies: int = 0
    today_pnl: float = 0.0
    regime: Optional[str] = None
    status: str = "OFF"
    trading_hours: dict = Field(default_factory=dict)
    current_candidate_id: Optional[str] = None
    live_enabled_at: Optional[str] = None
    sharpe_ratio: Optional[float] = None


class SymbolSwitchRequest(BaseModel):
    mode: str
    force: bool = False


class SymbolSwitchResponse(BaseModel):
    symbol: str
    mode: str
    message: str
    switched_at: str


@router.get(
    "/symbols",
    response_model=List[SymbolDetailResponse],
    summary="Get all symbols",
)
async def list_symbols(
    group: Optional[str] = Query(default=None),
    settings: Settings = Depends(get_config),
    db=Depends(get_db),
) -> List[SymbolDetailResponse]:
    all_symbols = settings.system.symbols.all_symbols
    
    # 获取数据库中的品种状态和今日盈亏
    today_pnl = get_today_pnl_by_symbol(db)
    
    result = []
    for symbol, config in all_symbols.items():
        if group and config.group != group:
            continue
        
        # 获取品种开关状态
        switch = get_symbol_switch(db, symbol)
        
        # 检查是否有运行中的策略
        running_candidate = get_running_candidate_by_symbol(db, symbol)
        
        result.append(SymbolDetailResponse(
            symbol=symbol,
            name=config.name,
            exchange=config.exchange,
            group=config.group,
            lot=config.lot,
            margin_rate=config.margin_rate,
            max_margin=config.max_margin,
            evolution_pool=config.evolution_pool,
            trading_hours=config.trading_hours.dict(),
            status=switch.mode.value if switch else "OFF",
            today_pnl=today_pnl.get(symbol, 0.0),
            running_strategies=1 if running_candidate else 0,
            current_candidate_id=switch.current_candidate_id if switch else None,
            live_enabled_at=switch.live_enabled_at.isoformat() if (switch and switch.live_enabled_at) else None,
            sharpe_ratio=running_candidate.sharpe_paper_5d if running_candidate else None,
        ))
    return result


@router.get(
    "/symbols/{symbol}",
    response_model=SymbolDetailResponse,
    summary="Get symbol detail",
)
async def get_symbol(
    symbol: str,
    settings: Settings = Depends(get_config),
    db=Depends(get_db),
) -> SymbolDetailResponse:
    all_symbols = settings.system.symbols.all_symbols
    if symbol not in all_symbols:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {symbol} not found",
        )
    
    config = all_symbols[symbol]
    
    # 获取数据库中的品种状态
    switch = get_symbol_switch(db, symbol)
    
    # 获取今日盈亏
    today_pnl = get_today_pnl_by_symbol(db)
    
    # 检查是否有运行中的策略
    running_candidate = get_running_candidate_by_symbol(db, symbol)
    
    return SymbolDetailResponse(
        symbol=symbol,
        name=config.name,
        exchange=config.exchange,
        group=config.group,
        lot=config.lot,
        margin_rate=config.margin_rate,
        max_margin=config.max_margin,
        evolution_pool=config.evolution_pool,
        trading_hours=config.trading_hours.dict(),
        status=switch.mode.value if switch else "OFF",
        today_pnl=today_pnl.get(symbol, 0.0),
        running_strategies=1 if running_candidate else 0,
        current_candidate_id=switch.current_candidate_id if switch else None,
        live_enabled_at=switch.live_enabled_at.isoformat() if (switch and switch.live_enabled_at) else None,
    )


@router.put(
    "/symbols/{symbol}/mode",
    response_model=SymbolSwitchResponse,
    summary="Switch symbol trading mode",
)
async def switch_symbol_mode(
    symbol: str,
    request: SymbolSwitchRequest,
    settings: Settings = Depends(get_config),
    db=Depends(get_db),
) -> SymbolSwitchResponse:
    all_symbols = settings.system.symbols.all_symbols
    if symbol not in all_symbols:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {symbol} not found",
        )
    
    valid_modes = ["OFF", "PAPER", "LIVE"]
    if request.mode not in valid_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {request.mode}. Valid modes: {valid_modes}",
        )
    
    # 切换到 LIVE 模式需要有运行中的策略
    if request.mode == "LIVE" and not request.force:
        running_candidate = get_running_candidate_by_symbol(db, symbol)
        if not running_candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot switch to LIVE mode: no running strategy found for this symbol",
            )
    
    # 更新数据库中的模式
    new_mode = SymbolMode(request.mode)
    switch = update_symbol_mode(db, symbol, new_mode)
    
    return SymbolSwitchResponse(
        symbol=symbol,
        mode=switch.mode.value,
        message=f"Successfully switched to {request.mode} mode",
        switched_at=switch.last_switch_at.isoformat(),
    )

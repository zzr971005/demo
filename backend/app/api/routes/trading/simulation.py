"""
模拟交易API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select
import uuid
import numpy as np

from app.db import get_session
from app.models import SimulationSession, SimulationOrder, SimulationPosition

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class SimulationRequest(BaseModel):
    symbol: str
    strategy_id: str
    volume: int
    direction: str


class SimulationResponse(BaseModel):
    success: bool
    message: str
    order_id: Optional[str] = None
    status: Optional[str] = None


class SimulationStartRequest(BaseModel):
    mode: str = "tqkq"
    initial_balance: float = 1000000.0


@router.post("/start")
async def start_simulation(request: SimulationStartRequest = SimulationStartRequest()) -> Dict[str, Any]:
    """启动模拟交易"""
    with get_session() as session:
        # Check if already running
        query = select(SimulationSession).where(SimulationSession.status == "RUNNING").limit(1)
        result = session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            return {
                "success": True,
                "message": "Simulation already running",
                "session_id": existing.id,
            }

        # Create new simulation session
        new_session = SimulationSession(
            mode=request.mode,
            status="RUNNING",
            initial_balance=request.initial_balance,
            account_balance=request.initial_balance,
        )
        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        return {
            "success": True,
            "message": "Simulation started",
            "session_id": new_session.id,
        }


@router.get("/status")
async def get_simulation_status() -> Dict[str, Any]:
    """获取模拟交易状态"""
    with get_session() as session:
        # Get the most recent simulation session
        query = select(SimulationSession).order_by(SimulationSession.created_at.desc()).limit(1)
        result = session.execute(query)
        session_data = result.scalar_one_or_none()
        
        if session_data:
            return {
                "is_running": session_data.status == "RUNNING",
                "mode": session_data.mode,
                "session_id": session_data.id,
                "account_balance": float(session_data.account_balance),
                "initial_balance": float(session_data.initial_balance),
            }
        else:
            # Return default status if no session exists
            return {
                "is_running": False,
                "mode": "tqkq",
                "positions": {},
                "account_balance": 1000000.0
            }


@router.post("/order", response_model=SimulationResponse)
async def place_simulation_order(request: SimulationRequest) -> SimulationResponse:
    """下模拟订单"""
    with get_session() as session:
        # Get or create a simulation session
        query = select(SimulationSession).order_by(SimulationSession.created_at.desc()).limit(1)
        result = session.execute(query)
        session_data = result.scalar_one_or_none()
        
        if not session_data or session_data.status != "RUNNING":
            # Create a new session
            session_id = f"sim_{uuid.uuid4().hex[:16]}"
            session_data = SimulationSession(
                id=session_id,
                symbol=request.symbol.upper(),
                strategy_id=request.strategy_id,
                mode="tqkq",
                status="RUNNING",
                account_balance=1000000.0,
                initial_balance=1000000.0,
                start_time=datetime.utcnow(),
            )
            session.add(session_data)
            session.commit()
        
        # Create simulation order
        order_id = f"order_{uuid.uuid4().hex[:16]}"
        new_order = SimulationOrder(
            id=order_id,
            session_id=session_data.id,
            symbol=request.symbol.upper(),
            strategy_id=request.strategy_id,
            direction=request.direction.upper(),
            volume=request.volume,
            order_type="MARKET",
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        session.add(new_order)
        session.commit()
        
        return SimulationResponse(
            success=True,
            message="模拟订单已提交",
            order_id=order_id,
            status="PENDING"
        )


@router.get("/positions")
async def get_simulation_positions() -> Dict[str, Any]:
    """获取模拟持仓"""
    with get_session() as session:
        # Get the most recent simulation session
        query = select(SimulationSession).order_by(SimulationSession.created_at.desc()).limit(1)
        result = session.execute(query)
        session_data = result.scalar_one_or_none()
        
        if not session_data:
            return {"positions": []}
        
        # Get positions for this session
        query = select(SimulationPosition).where(SimulationPosition.session_id == session_data.id)
        result = session.execute(query)
        positions = result.scalars().all()
        
        return {
            "positions": [
                {
                    "symbol": p.symbol,
                    "strategy_id": p.strategy_id,
                    "direction": p.direction,
                    "volume": p.volume,
                    "entry_price": float(p.entry_price),
                    "current_price": float(p.current_price) if p.current_price else None,
                    "unrealized_pnl": float(p.unrealized_pnl) if p.unrealized_pnl else 0.0,
                }
                for p in positions
            ]
        }


@router.get("/orders")
async def get_simulation_orders(
    symbol: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """获取模拟订单"""
    with get_session() as session:
        # Get the most recent simulation session
        query = select(SimulationSession).order_by(SimulationSession.created_at.desc()).limit(1)
        result = session.execute(query)
        session_data = result.scalar_one_or_none()
        
        if not session_data:
            return {"orders": []}
        
        # Get orders for this session
        query = select(SimulationOrder).where(SimulationOrder.session_id == session_data.id)
        
        if symbol:
            query = query.where(SimulationOrder.symbol == symbol.upper())
        
        query = query.order_by(SimulationOrder.created_at.desc()).limit(limit)
        result = session.execute(query)
        orders = result.scalars().all()
        
        return {
            "orders": [
                {
                    "id": o.id,
                    "symbol": o.symbol,
                    "strategy_id": o.strategy_id,
                    "direction": o.direction,
                    "volume": o.volume,
                    "price": float(o.price) if o.price else None,
                    "order_type": o.order_type,
                    "status": o.status,
                    "filled_volume": o.filled_volume,
                    "filled_price": float(o.filled_price) if o.filled_price else None,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ]
        }


@router.get("/performance")
async def get_simulation_performance(
    symbol: Optional[str] = None,
    strategy_id: Optional[str] = None
) -> Dict[str, Any]:
    """获取模拟绩效"""
    with get_session() as session:
        # Get the most recent simulation session
        query = select(SimulationSession).order_by(SimulationSession.created_at.desc()).limit(1)
        result = session.execute(query)
        session_data = result.scalar_one_or_none()
        
        if not session_data:
            return {
                "total_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0
            }
        
        # Calculate performance from session data
        initial_balance = float(session_data.initial_balance)
        current_balance = float(session_data.account_balance)
        total_return = (current_balance - initial_balance) / initial_balance if initial_balance > 0 else 0.0
        
        # Get all orders for this session to calculate performance metrics
        query = select(SimulationOrder).where(SimulationOrder.session_id == session_data.id)
        
        if symbol:
            query = query.where(SimulationOrder.symbol == symbol.upper())
        if strategy_id:
            query = query.where(SimulationOrder.strategy_id == strategy_id)
        
        query = query.order_by(SimulationOrder.created_at)
        result = session.execute(query)
        orders = result.scalars().all()
        
        # Calculate performance metrics from order history
        if not orders:
            return {
                "total_return": total_return,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0
            }
        
        # Calculate PnL for each filled order
        pnl_list = []
        total_trades = 0
        winning_trades = 0
        
        for order in orders:
            if order.status == "FILLED" and order.filled_price and order.filled_volume:
                # Calculate PnL based on direction
                if order.direction == "BUY":
                    # Long position: profit = (current_price - entry_price) * volume
                    pnl = (float(order.filled_price) - float(order.price)) * order.filled_volume if order.price else 0.0
                else:
                    # Short position: profit = (entry_price - current_price) * volume
                    pnl = (float(order.price) - float(order.filled_price)) * order.filled_volume if order.price else 0.0
                
                pnl_list.append(pnl)
                total_trades += 1
                if pnl > 0:
                    winning_trades += 1
        
        # Calculate Sharpe ratio (annualized)
        if len(pnl_list) > 1:
            returns = np.array(pnl_list) / initial_balance
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Calculate max drawdown
        if len(pnl_list) > 0:
            cumulative_pnl = np.cumsum(pnl_list)
            peak = np.maximum.accumulate(cumulative_pnl)
            drawdown = (peak - cumulative_pnl) / initial_balance
            max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0.0
        else:
            max_drawdown = 0.0
        
        # Calculate win rate
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate
        }

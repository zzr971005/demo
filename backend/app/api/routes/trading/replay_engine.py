"""
历史回放API - 新路径，不冲突
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import select
import uuid

from app.db import get_session
from app.models import ReplaySession as ReplaySessionModel

router = APIRouter(prefix="/api/replay-engine", tags=["replay-engine"])


class ReplayStartRequest(BaseModel):
    symbol: str
    start_time: str
    end_time: str
    speed: int = 1


class ReplaySessionResponse(BaseModel):
    session_id: str
    symbol: str
    start_time: str
    end_time: str
    status: str
    current_time: str
    speed: int


@router.post("/start")
async def start_replay(request: ReplayStartRequest) -> Dict[str, Any]:
    """启动历史回放"""
    with get_session() as session:
        session_id = f"replay_{uuid.uuid4().hex[:16]}"
        
        # Parse datetime strings
        start_dt = datetime.fromisoformat(request.start_time)
        end_dt = datetime.fromisoformat(request.end_time)
        
        replay_session = ReplaySessionModel(
            session_id=session_id,
            symbol=request.symbol.upper(),
            start_date=start_dt,
            end_date=end_dt,
            data_source="local",
            status="running",
            started_at=datetime.utcnow(),
        )
        session.add(replay_session)
        session.commit()
        
        return {
            "session_id": session_id,
            "symbol": request.symbol,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "status": "running",
            "current_time": request.start_time,
            "speed": request.speed,
        }


@router.post("/pause/{session_id}")
async def pause_replay(session_id: str) -> Dict[str, Any]:
    """暂停回放"""
    with get_session() as session:
        query = select(ReplaySessionModel).where(ReplaySessionModel.session_id == session_id)
        result = session.execute(query)
        replay_session = result.scalar_one_or_none()
        
        if replay_session:
            replay_session.status = "paused"
            session.commit()
        
        return {"status": "paused"}


@router.post("/resume/{session_id}")
async def resume_replay(session_id: str) -> Dict[str, Any]:
    """继续回放"""
    with get_session() as session:
        query = select(ReplaySessionModel).where(ReplaySessionModel.session_id == session_id)
        result = session.execute(query)
        replay_session = result.scalar_one_or_none()
        
        if replay_session:
            replay_session.status = "running"
            session.commit()
        
        return {"status": "running"}


@router.post("/stop/{session_id}")
async def stop_replay(session_id: str) -> Dict[str, Any]:
    """停止回放"""
    with get_session() as session:
        query = select(ReplaySessionModel).where(ReplaySessionModel.session_id == session_id)
        result = session.execute(query)
        replay_session = result.scalar_one_or_none()
        
        if replay_session:
            replay_session.status = "completed"
            replay_session.completed_at = datetime.utcnow()
            session.commit()
        
        return {"status": "stopped"}


@router.post("/speed/{session_id}")
async def set_speed(session_id: str, speed: int) -> Dict[str, Any]:
    """设置回放速度"""
    # Speed is managed in-memory for live replay, not persisted
    return {"speed": speed}

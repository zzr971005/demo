"""
PostgreSQL 业务数据读写中心

负责：
- 候选策略状态管理
- 交易记录读写
- 品种开关状态
- 进化世代记录
- 风控事件记录

替代分散的SQLite使用，统一通过DataHub访问
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
    insert,
    select,
    update,
    delete,
    text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/quant_db"
)

Base = declarative_base()


class Candidate(Base):
    """候选策略模型"""
    __tablename__ = "candidates"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(64), primary_key=True)
    symbol = Column(String(16), nullable=False, index=True)
    status = Column(String(16), default="SEED", index=True)
    strategy_type = Column(String(32))
    formula = Column(Text, nullable=False)
    params = Column(Text)
    parent_id = Column(String(64))
    generation = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sharpe_train = Column(Float)
    sharpe_val = Column(Float)
    sharpe_test = Column(Float)
    sharpe_paper_5d = Column(Float)
    max_drawdown = Column(Float)
    calmar = Column(Float)
    total_trades = Column(Integer)
    win_rate = Column(Float)
    avg_holding_hours = Column(Float)
    is_seed = Column(Boolean, default=False)
    seed_code = Column(String(16))
    deployed_at = Column(DateTime)
    degraded_at = Column(DateTime)
    retired_at = Column(DateTime)
    retire_reason = Column(Text)
    notes = Column(Text)


class Trade(Base):
    """交易记录模型"""
    __tablename__ = "trades"
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(64), primary_key=True)
    symbol = Column(String(16), nullable=False, index=True)
    candidate_id = Column(String(64), index=True)
    direction = Column(String(8), nullable=False)
    offset = Column(String(16), nullable=False)
    open_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float)
    volume = Column(Integer, nullable=False)
    pnl = Column(Float)
    fee = Column(Float)
    status = Column(String(16), default="OPEN", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvolutionGeneration(Base):
    """进化世代记录模型"""
    __tablename__ = "evolution_generations"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    generation = Column(Integer, nullable=False)
    stage = Column(Integer, nullable=False)
    population_size = Column(Integer)
    elite_count = Column(Integer)
    mutation_rate = Column(Float)
    crossover_rate = Column(Float)
    best_fitness = Column(Float)
    avg_fitness = Column(Float)
    diversity_score = Column(Float)
    new_candidates = Column(Integer, default=0)
    pruned_candidates = Column(Integer, default=0)
    runtime_seconds = Column(Float)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    log_path = Column(String(256))
    notes = Column(Text)


class RiskEvent(Base):
    """风控事件模型"""
    __tablename__ = "risk_events"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), index=True)
    event_type = Column(String(32), nullable=False)
    level = Column(Integer, nullable=False)
    message = Column(Text)
    triggered_at = Column(DateTime, nullable=False, index=True)
    resolved_at = Column(DateTime)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SymbolSwitch(Base):
    """品种开关状态模型"""
    __tablename__ = "symbol_switches"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, unique=True)
    mode = Column(String(16))
    current_candidate_id = Column(String(64))
    paper_candidate_id = Column(String(64))
    group_name = Column(String(32))
    margin_per_lot = Column(Integer)
    max_lots = Column(Integer)
    is_priority = Column(Boolean, default=False)
    live_enabled_at = Column(DateTime)
    last_switch_at = Column(DateTime)
    switch_reason = Column(Text)
    operator = Column(String(32))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostgresHub:
    """PostgreSQL业务数据访问中心"""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or DEFAULT_DATABASE_URL
        self.engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._connect()
        self._ensure_tables()
    
    def _connect(self) -> None:
        """建立数据库连接"""
        self.engine = create_engine(self.db_url, echo=False)
        self._session_factory = sessionmaker(bind=self.engine)
    
    def _ensure_tables(self) -> None:
        """确保所有表已创建"""
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self._session_factory()
    
    # ========== 候选策略操作 ==========
    
    def save_candidate(self, data: Dict[str, Any]) -> None:
        """保存候选策略"""
        with self.get_session() as session:
            candidate = Candidate(**data)
            session.merge(candidate)
    
    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """获取候选策略"""
        with self.get_session() as session:
            candidate = session.query(Candidate).filter(Candidate.id == candidate_id).first()
            if candidate:
                return {c.name: getattr(candidate, c.name) for c in Candidate.__table__.columns}
            return None
    
    def query_candidates(self, symbol: Optional[str] = None, 
                        status: Optional[str] = None,
                        is_active: Optional[bool] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """查询候选策略列表"""
        with self.get_session() as session:
            query = session.query(Candidate)
            if symbol:
                query = query.filter(Candidate.symbol == symbol)
            if status:
                query = query.filter(Candidate.status == status)
            if is_active is not None:
                query = query.filter(Candidate.is_active == is_active)
            query = query.order_by(Candidate.created_at.desc()).limit(limit)
            results = []
            for candidate in query.all():
                results.append({c.name: getattr(candidate, c.name) for c in Candidate.__table__.columns})
            return results
    
    def update_candidate(self, candidate_id: str, updates: Dict[str, Any]) -> None:
        """更新候选策略"""
        with self.get_session() as session:
            session.query(Candidate).filter(Candidate.id == candidate_id).update(updates)
    
    def delete_candidate(self, candidate_id: str) -> None:
        """删除候选策略"""
        with self.get_session() as session:
            session.query(Candidate).filter(Candidate.id == candidate_id).delete()
    
    # ========== 交易记录操作 ==========
    
    def save_trade(self, data: Dict[str, Any]) -> None:
        """保存交易记录"""
        with self.get_session() as session:
            trade = Trade(**data)
            session.add(trade)
    
    def query_trades(self, symbol: Optional[str] = None,
                    candidate_id: Optional[str] = None,
                    status: Optional[str] = None,
                    limit: int = 100) -> List[Dict[str, Any]]:
        """查询交易记录"""
        with self.get_session() as session:
            query = session.query(Trade)
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if candidate_id:
                query = query.filter(Trade.candidate_id == candidate_id)
            if status:
                query = query.filter(Trade.status == status)
            query = query.order_by(Trade.open_time.desc()).limit(limit)
            results = []
            for trade in query.all():
                results.append({c.name: getattr(trade, c.name) for c in Trade.__table__.columns})
            return results
    
    def update_trade(self, trade_id: str, updates: Dict[str, Any]) -> None:
        """更新交易记录"""
        with self.get_session() as session:
            session.query(Trade).filter(Trade.id == trade_id).update(updates)
    
    # ========== 进化世代操作 ==========
    
    def save_evolution_generation(self, data: Dict[str, Any]) -> None:
        """保存进化世代记录"""
        with self.get_session() as session:
            gen = EvolutionGeneration(**data)
            session.add(gen)
    
    def get_latest_generation(self, symbol: str, stage: str) -> Optional[int]:
        """获取最新进化世代"""
        with self.get_session() as session:
            gen = session.query(EvolutionGeneration)\
                .filter(EvolutionGeneration.symbol == symbol,
                        EvolutionGeneration.stage == stage)\
                .order_by(EvolutionGeneration.generation.desc())\
                .first()
            return gen.generation if gen else 0
    
    # ========== 风控事件操作 ==========
    
    def save_risk_event(self, data: Dict[str, Any]) -> None:
        """保存风控事件"""
        with self.get_session() as session:
            event = RiskEvent(**data)
            session.add(event)
    
    def query_risk_events(self, symbol: Optional[str] = None,
                         is_resolved: Optional[bool] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """查询风控事件"""
        with self.get_session() as session:
            query = session.query(RiskEvent)
            if symbol:
                query = query.filter(RiskEvent.symbol == symbol)
            if is_resolved is not None:
                query = query.filter(RiskEvent.is_resolved == is_resolved)
            query = query.order_by(RiskEvent.triggered_at.desc()).limit(limit)
            results = []
            for event in query.all():
                results.append({c.name: getattr(event, c.name) for c in RiskEvent.__table__.columns})
            return results
    
    # ========== 品种开关操作 ==========
    
    def get_symbol_switch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取品种开关状态"""
        with self.get_session() as session:
            switch = session.query(SymbolSwitch).filter(SymbolSwitch.symbol == symbol).first()
            if switch:
                return {c.name: getattr(switch, c.name) for c in SymbolSwitch.__table__.columns}
            return None
    
    def set_symbol_switch(self, symbol: str, mode: str, config: Optional[str] = None) -> None:
        """设置品种开关状态"""
        with self.get_session() as session:
            try:
                switch = session.query(SymbolSwitch).filter(SymbolSwitch.symbol == symbol).first()
                if switch:
                    switch.mode = mode
                else:
                    switch = SymbolSwitch(symbol=symbol, mode=mode)
                    session.add(switch)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"设置品种开关失败: {e}")
                raise
    
    def get_all_symbol_switches(self) -> List[Dict[str, Any]]:
        """获取所有品种开关状态"""
        with self.get_session() as session:
            results = []
            for switch in session.query(SymbolSwitch).all():
                results.append({c.name: getattr(switch, c.name) for c in SymbolSwitch.__table__.columns})
            return results

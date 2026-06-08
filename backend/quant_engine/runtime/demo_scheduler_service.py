"""
模拟盘调度服??Task 11

职责?
- Paper状态品种的自动运行调度
- 模拟盘绩效跟踪与记录
- Paper ?Deployable 自动晋升
- ?candidate_core 状态机联动
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.config import get_settings
from app.models import Candidate, CandidateStatus, SymbolMode, SymbolSwitch
from core.candidate_core import CandidateStateMachine
from runtime.execution_gateway import ExecutionGateway
from runtime.risk_monitor import RiskMonitor
from strategy.position_lifecycle import PositionLifecycleManager
from strategy.spec import SignalDirection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class PaperPerformance:
    """模拟盘绩效记?""

    candidate_id: str
    symbol: str
    start_at: datetime
    end_at: Optional[datetime] = None
    total_return: float = 0.0
    sharpe: Optional[float] = None
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    avg_holding_hours: float = 0.0
    is_promotable: bool = False
    promotion_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "total_return": self.total_return,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "avg_holding_hours": self.avg_holding_hours,
            "is_promotable": self.is_promotable,
            "promotion_reason": self.promotion_reason,
        }


@dataclass
class PaperRunSession:
    """单次模拟盘运行会?""

    session_id: str
    symbol: str
    candidate_id: str
    started_at: datetime
    data_frequency: str = "1m"
    is_running: bool = False
    last_run_at: Optional[datetime] = None
    error_count: int = 0
    max_errors: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "symbol": self.symbol,
            "candidate_id": self.candidate_id,
            "started_at": self.started_at.isoformat(),
            "data_frequency": self.data_frequency,
            "is_running": self.is_running,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "error_count": self.error_count,
        }


# ---------------------------------------------------------------------------
# 模拟盘调度服?
# ---------------------------------------------------------------------------

class DemoSchedulerService:
    """
    模拟盘调度服?

    自动调度和管理所有处?PAPER 状态的候选策略：
    - 定时运行策略信号生成
    - 跟踪模拟盘绩?
    - 满足条件时自动晋升到 DEPLOYABLE
    """

    PROMOTION_MIN_SHARPE: float = 0.8
    PROMOTION_MIN_DAYS: int = 5
    PROMOTION_MAX_DD: float = 0.08
    PROMOTION_MIN_TRADES: int = 3

    def __init__(
        self,
        state_machine: CandidateStateMachine,
        risk_monitor: RiskMonitor,
        gateway: ExecutionGateway,
        position_manager: PositionLifecycleManager,
        redis_client: Optional[Any] = None,
    ) -> None:
        self.sm = state_machine
        self.risk = risk_monitor
        self.gateway = gateway
        self.pm = position_manager
        self.redis = redis_client

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # 会话与绩效跟?
        self._sessions: Dict[str, PaperRunSession] = {}
        self._performance: Dict[str, PaperPerformance] = {}
        self._symbol_candidate_map: Dict[str, str] = {}

    # -----------------------------------------------------------------------
    # 生命周期
    # -----------------------------------------------------------------------

    async def start(self, interval_seconds: float = 60.0) -> None:
        """启动模拟盘调度服务?""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop(interval_seconds))
        logger.info(f"模拟盘调度服务已启动，轮询间?{interval_seconds}s")

    async def stop(self) -> None:
        """停止模拟盘调度服务?""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # 停止所有会?
        for session in self._sessions.values():
            session.is_running = False
        self._sessions.clear()
        logger.info("模拟盘调度服务已停止")

    async def _scheduler_loop(self, interval: float) -> None:
        """调度主循环?""
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.exception(f"模拟盘调度异? {e}")
            await asyncio.sleep(interval)

    async def run_once(self) -> List[PaperPerformance]:
        """
        执行一次完整调度?

        1. 扫描所?PAPER 状态候?
        2. 运行策略信号
        3. 更新绩效
        4. 检查晋升条?
        """
        performances: List[PaperPerformance] = []

        # 注意：实际应从数据库查询 PAPER 状态候?
        # 此处简化，依赖外部注入候选列表或从缓存获?
        paper_candidates = await self._fetch_paper_candidates()

        for candidate in paper_candidates:
            try:
                perf = await self._run_paper_candidate(candidate)
                if perf:
                    performances.append(perf)
            except Exception as e:
                logger.exception(f"[{candidate.symbol}] 模拟盘运行异? {e}")

        return performances

    # -----------------------------------------------------------------------
    # 候选运?
    # -----------------------------------------------------------------------

    async def _run_paper_candidate(self, candidate: Candidate) -> Optional[PaperPerformance]:
        """运行单个模拟盘候选?""
        if candidate.status != CandidateStatus.PAPER:
            return None

        symbol = candidate.symbol
        session = self._get_or_create_session(candidate)

        if session.error_count >= session.max_errors:
            logger.warning(f"[{symbol}] 会话错误过多，跳?)
            return None

        session.is_running = True
        session.last_run_at = datetime.utcnow()

        # 风控检?
        if self.risk.is_symbol_paused(symbol):
            logger.info(f"[{symbol}] 品种被风控暂停，跳过模拟盘运?)
            return None

        # 模拟执行（简化：实际应调?StrategyRunner?
        # 这里仅更新绩效跟踪数?
        perf = self._update_performance(candidate)

        # 检查晋?
        await self._check_promotion(candidate, perf)

        session.is_running = False
        return perf

    def _get_or_create_session(self, candidate: Candidate) -> PaperRunSession:
        """获取或创建运行会话?""
        session_id = f"paper:{candidate.id}"
        if session_id not in self._sessions:
            self._sessions[session_id] = PaperRunSession(
                session_id=session_id,
                symbol=candidate.symbol,
                candidate_id=candidate.id,
                started_at=datetime.utcnow(),
            )
        return self._sessions[session_id]

    # -----------------------------------------------------------------------
    # 绩效跟踪
    # -----------------------------------------------------------------------

    def _update_performance(self, candidate: Candidate) -> PaperPerformance:
        """更新模拟盘绩效?""
        perf = self._performance.get(candidate.id)
        if perf is None:
            perf = PaperPerformance(
                candidate_id=candidate.id,
                symbol=candidate.symbol,
                start_at=candidate.deployed_at or datetime.utcnow(),
            )
            self._performance[candidate.id] = perf

        # 从候选已有字段更?
        perf.sharpe = candidate.sharpe_paper_5d
        perf.max_drawdown = candidate.max_drawdown or 0.0
        perf.win_rate = candidate.win_rate or 0.0
        perf.total_trades = candidate.total_trades or 0
        perf.avg_holding_hours = candidate.avg_holding_hours or 0.0

        # 使用实际的总收益率（不是夏普比率）
        if candidate.total_return is not None:
            perf.total_return = candidate.total_return
        # 回退：如果没有 total_return，暂时设为 0，避免错误的计算
        else:
            perf.total_return = 0.0

        return perf

    async def _check_promotion(
        self,
        candidate: Candidate,
        perf: PaperPerformance,
    ) -> Tuple[bool, str]:
        """
        检?Paper ?Deployable 晋升条件?

        晋升标准?
        - Paper夏普 >= PROMOTION_MIN_SHARPE
        - 运行天数 >= PROMOTION_MIN_DAYS
        - 最大回?<= PROMOTION_MAX_DD
        - 交易笔数 >= PROMOTION_MIN_TRADES
        """
        if candidate.status != CandidateStatus.PAPER:
            return False, "非PAPER状?

        # 检查运行天?
        paper_days = 0
        if candidate.deployed_at:
            paper_days = (datetime.utcnow() - candidate.deployed_at).days

        if paper_days < self.PROMOTION_MIN_DAYS:
            return False, f"运行 {paper_days} 天，不足 {self.PROMOTION_MIN_DAYS} ?

        # 检查夏?
        sharpe = perf.sharpe or 0.0
        if sharpe < self.PROMOTION_MIN_SHARPE:
            return False, f"夏普 {sharpe:.3f} 低于门槛 {self.PROMOTION_MIN_SHARPE}"

        # 检查回?
        if perf.max_drawdown > self.PROMOTION_MAX_DD:
            return False, f"回撤 {perf.max_drawdown:.2%} 超过门槛 {self.PROMOTION_MAX_DD:.2%}"

        # 检查交易笔?
        if perf.total_trades < self.PROMOTION_MIN_TRADES:
            return False, f"交易 {perf.total_trades} 笔，不足 {self.PROMOTION_MIN_TRADES} ?

        # 执行晋升
        perf.is_promotable = True
        perf.promotion_reason = (
            f"Paper表现达标: 夏普={sharpe:.3f}, 回撤={perf.max_drawdown:.2%}, "
            f"运行={paper_days}? 交易={perf.total_trades}?
        )

        ok, msg = await self.sm.transition(
            candidate=candidate,
            target_status=CandidateStatus.DEPLOYABLE,
            reason=perf.promotion_reason,
            metadata={"paper_sharpe": sharpe, "paper_days": paper_days, "paper_trades": perf.total_trades},
        )

        if ok:
            perf.end_at = datetime.utcnow()
            await self._publish_promotion_event(candidate, perf)
            logger.info(f"[{candidate.symbol}] 候?{candidate.id} 晋升 DEPLOYABLE: {msg}")

        return ok, msg

    # -----------------------------------------------------------------------
    # 数据获取（简化占位）
    # -----------------------------------------------------------------------

    async def _fetch_paper_candidates(self) -> List[Candidate]:
        """
        获取所?PAPER 状态候选?

        实际应从数据库查询，此处返回空列表作为占位?
        外部系统应通过 register_paper_candidate 注入候选?
        """
        return []

    def register_paper_candidate(self, candidate: Candidate) -> None:
        """注册模拟盘候选到调度服务?""
        if candidate.status != CandidateStatus.PAPER:
            logger.warning(f"候?{candidate.id} 不是PAPER状态，跳过注册")
            return
        self._symbol_candidate_map[candidate.symbol] = candidate.id
        logger.info(f"[{candidate.symbol}] 注册模拟盘候?{candidate.id}")

    def unregister_paper_candidate(self, candidate_id: str) -> None:
        """注销模拟盘候选?""
        self._performance.pop(candidate_id, None)
        self._sessions.pop(f"paper:{candidate_id}", None)
        for symbol, cid in list(self._symbol_candidate_map.items()):
            if cid == candidate_id:
                del self._symbol_candidate_map[symbol]
                break

    # -----------------------------------------------------------------------
    # 查询接口
    # -----------------------------------------------------------------------

    def get_performance(self, candidate_id: str) -> Optional[PaperPerformance]:
        """获取候选的模拟盘绩效?""
        return self._performance.get(candidate_id)

    def get_all_performances(self) -> List[PaperPerformance]:
        """获取所有模拟盘绩效?""
        return list(self._performance.values())

    def get_session(self, candidate_id: str) -> Optional[PaperRunSession]:
        """获取运行会话?""
        return self._sessions.get(f"paper:{candidate_id}")

    # -----------------------------------------------------------------------
    # 事件发布
    # -----------------------------------------------------------------------

    async def _publish_promotion_event(
        self,
        candidate: Candidate,
        perf: PaperPerformance,
    ) -> None:
        if self.redis is None:
            return
        try:
            event = {
                "type": "paper_promotion",
                "candidate_id": candidate.id,
                "symbol": candidate.symbol,
                "performance": perf.to_dict(),
                "timestamp": datetime.utcnow().isoformat(),
            }
            await self.redis.publish("paper:promotions", json.dumps(event, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"晋升事件发布失败: {e}")

    async def _publish_paper_heartbeat(self, session: PaperRunSession) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.publish(
                "paper:heartbeat",
                json.dumps(session.to_dict(), ensure_ascii=False),
            )
        except Exception as e:
            logger.warning(f"心跳发布失败: {e}")


# ---------------------------------------------------------------------------
# Paper 绩效聚合?
# ---------------------------------------------------------------------------

class PaperPerformanceAggregator:
    """
    模拟盘绩效聚合器

    按品?组别聚合模拟盘绩效，生成日报/周报?
    """

    def __init__(self, service: DemoSchedulerService) -> None:
        self.service = service

    def aggregate_by_symbol(self) -> Dict[str, Dict[str, Any]]:
        """按品种聚合绩效?""
        result: Dict[str, Dict[str, Any]] = {}
        for perf in self.service.get_all_performances():
            symbol = perf.symbol
            if symbol not in result:
                result[symbol] = {
                    "symbol": symbol,
                    "candidates": [],
                    "best_sharpe": None,
                    "worst_dd": None,
                    "total_trades": 0,
                }
            result[symbol]["candidates"].append(perf.to_dict())
            if perf.sharpe is not None:
                if result[symbol]["best_sharpe"] is None or perf.sharpe > result[symbol]["best_sharpe"]:
                    result[symbol]["best_sharpe"] = perf.sharpe
            if result[symbol]["worst_dd"] is None or perf.max_drawdown > result[symbol]["worst_dd"]:
                result[symbol]["worst_dd"] = perf.max_drawdown
            result[symbol]["total_trades"] += perf.total_trades
        return result

    def get_promotion_candidates(self) -> List[PaperPerformance]:
        """获取所有可晋升的候选?""
        return [p for p in self.service.get_all_performances() if p.is_promotable]

    def generate_daily_report(self) -> Dict[str, Any]:
        """生成模拟盘日报?""
        all_perf = self.service.get_all_performances()
        total = len(all_perf)
        promotable = sum(1 for p in all_perf if p.is_promotable)
        avg_sharpe = sum(p.sharpe or 0 for p in all_perf) / total if total > 0 else 0.0
        avg_dd = sum(p.max_drawdown for p in all_perf) / total if total > 0 else 0.0

        return {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "total_paper_candidates": total,
            "promotable_count": promotable,
            "avg_sharpe": round(avg_sharpe, 4),
            "avg_max_drawdown": round(avg_dd, 4),
            "by_symbol": self.aggregate_by_symbol(),
            "generated_at": datetime.utcnow().isoformat(),
        }

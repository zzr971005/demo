"""
åéç­ç¥ç¶ææº â?å¨çå½å¨æç®¡ç?
ç¶ææµè½¬ï¼
    SEED â?BACKTEST â?PAPER â?DEPLOYABLE â?RUNNING â?DEGRADED â?RETIRED

æ ¸å¿è½åï¼?- ç¶æè½¬æ¢éªè¯ï¼éæ³æµè½¬æç»ï¼?- èªå¨æ¿æ¢é»è¾ï¼PaperææRunningï¼?- åæ¤å¼ºå¶éçº§ï¼?8%ï¼?- Regimeä¸å¹éæå?- Redisäºä»¶åå¸
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models import Candidate, CandidateStatus, SQLiteBase
from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ç¶æè½¬æ¢å¾
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: Dict[CandidateStatus, Set[CandidateStatus]] = {
    CandidateStatus.SEED: {
        CandidateStatus.BACKTEST,
        CandidateStatus.RETIRED,
    },
    CandidateStatus.BACKTEST: {
        CandidateStatus.PAPER,
        CandidateStatus.DEGRADED,
        CandidateStatus.RETIRED,
    },
    CandidateStatus.PAPER: {
        CandidateStatus.DEPLOYABLE,
        CandidateStatus.RUNNING,
        CandidateStatus.DEGRADED,
        CandidateStatus.RETIRED,
    },
    CandidateStatus.DEPLOYABLE: {
        CandidateStatus.RUNNING,
        CandidateStatus.DEGRADED,
        CandidateStatus.RETIRED,
    },
    CandidateStatus.RUNNING: {
        CandidateStatus.DEGRADED,
        CandidateStatus.RETIRED,
    },
    CandidateStatus.DEGRADED: {
        CandidateStatus.PAPER,
        CandidateStatus.DEPLOYABLE,
        CandidateStatus.RETIRED,
    },
    CandidateStatus.RETIRED: set(),
}

# åè®¸ååéçº§/æ¢å¤çè·¯å¾?RECOVERY_TRANSITIONS: Dict[CandidateStatus, Set[CandidateStatus]] = {
    CandidateStatus.DEGRADED: {
        CandidateStatus.PAPER,
        CandidateStatus.DEPLOYABLE,
    },
}


# ---------------------------------------------------------------------------
# ç¶æåæ´äºä»?# ---------------------------------------------------------------------------

@dataclass
class StateTransitionEvent:
    candidate_id: str
    symbol: str
    from_status: CandidateStatus
    to_status: CandidateStatus
    triggered_at: datetime
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "triggered_at": self.triggered_at.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# ç¶ææºæ ¸å¿
# ---------------------------------------------------------------------------

class CandidateStateMachine:
    """åéç­ç¥ç¶ææºï¼ç®¡çå¨çå½å¨æç¶ææµè½¬ã?""

    DRAWDOWN_DEGRADE_THRESHOLD: float = 0.08
    PAPER_CHALLENGE_MIN_SHARPE: float = 0.5
    PAPER_CHALLENGE_MIN_DAYS: int = 10

    def __init__(self, redis_client: Optional[Any] = None) -> None:
        self.redis = redis_client
        self._lock = asyncio.Lock()

    def is_valid_transition(
        self,
        current: CandidateStatus,
        target: CandidateStatus,
    ) -> bool:
        """æ£æ¥ç¶æè½¬æ¢æ¯å¦åæ³ã?""
        if current == target:
            return True
        allowed = VALID_TRANSITIONS.get(current, set())
        return target in allowed

    def get_allowed_transitions(self, current: CandidateStatus) -> List[CandidateStatus]:
        """è·åå½åç¶æåè®¸çææç®æ ç¶æã?""
        return list(VALID_TRANSITIONS.get(current, set()))

    async def transition(
        self,
        candidate: Candidate,
        target_status: CandidateStatus,
        reason: str = "",
        db_session: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """
        æ§è¡ç¶æè½¬æ¢ã?
        Returns
        -------
        (success, message)
        """
        async with self._lock:
            current = candidate.status

            if not self.is_valid_transition(current, target_status):
                msg = (
                    f"éæ³ç¶ææµè½? {current.value} â?{target_status.value} "
                    f"(åé?{candidate.id})"
                )
                logger.warning(msg)
                return False, msg

            event = StateTransitionEvent(
                candidate_id=candidate.id,
                symbol=candidate.symbol,
                from_status=current,
                to_status=target_status,
                triggered_at=datetime.utcnow(),
                reason=reason,
                metadata=metadata or {},
            )

            candidate.status = target_status
            candidate.updated_at = datetime.utcnow()

            if target_status == CandidateStatus.RUNNING:
                candidate.deployed_at = datetime.utcnow()
            elif target_status == CandidateStatus.DEGRADED:
                candidate.degraded_at = datetime.utcnow()
            elif target_status == CandidateStatus.RETIRED:
                candidate.retired_at = datetime.utcnow()
                candidate.retire_reason = reason

            if db_session is not None:
                await db_session.commit()

            await self._publish_event(event)
            logger.info(
                f"[{candidate.symbol}] åé?{candidate.id} ç¶æåæ? "
                f"{current.value} â?{target_status.value} | åå : {reason}"
            )
            return True, f"ç¶æå·²åæ´: {current.value} â?{target_status.value}"

    async def force_degrade_on_drawdown(
        self,
        candidate: Candidate,
        current_drawdown: float,
        db_session: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """
        åæ¤è¶æ å¼ºå¶éçº§ã?
        Parameters
        ----------
        current_drawdown : float
            å½ååæ¤æ¯ä¾ï¼æ­£æ°ï¼å¦?0.085 è¡¨ç¤º 8.5%ï¼?        """
        if candidate.status not in (
            CandidateStatus.RUNNING,
            CandidateStatus.PAPER,
            CandidateStatus.DEPLOYABLE,
        ):
            return False, "å½åç¶æä¸æ¯æåæ¤éçº§"

        if current_drawdown <= self.DRAWDOWN_DEGRADE_THRESHOLD:
            return False, f"åæ¤ {current_drawdown:.2%} æªè¶è¿éå?

        return await self.transition(
            candidate=candidate,
            target_status=CandidateStatus.DEGRADED,
            reason=f"åæ¤è¶æ : {current_drawdown:.2%} > {self.DRAWDOWN_DEGRADE_THRESHOLD:.2%}",
            db_session=db_session,
            metadata={"drawdown": current_drawdown, "threshold": self.DRAWDOWN_DEGRADE_THRESHOLD},
        )

    async def pause_on_regime_mismatch(
        self,
        candidate: Candidate,
        current_regime: str,
        strategy_regime: str,
        db_session: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """
        Regimeä¸å¹éæ¶æåç­ç¥ï¼éçº§å°DEGRADEDï¼ã?        """
        if candidate.status != CandidateStatus.RUNNING:
            return False, "åªæRUNNINGç¶ææéè¦Regimeæ£æ?

        if current_regime == strategy_regime or strategy_regime == "ALL":
            return False, "Regimeå¹é"

        return await self.transition(
            candidate=candidate,
            target_status=CandidateStatus.DEGRADED,
            reason=f"Regimeä¸å¹é? å½å={current_regime}, ç­ç¥={strategy_regime}",
            db_session=db_session,
            metadata={"current_regime": current_regime, "strategy_regime": strategy_regime},
        )

    async def auto_paper_challenge(
        self,
        paper_candidate: Candidate,
        running_candidate: Candidate,
        db_session: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """
        PaperææRunningï¼æ¨¡æçè¡¨ç°ä¼äºå®çæ¶èªå¨æ¿æ¢ã?
        æ¿æ¢æ¡ä»¶ï¼?        - Paperå¤æ® > Runningå¤æ®
        - Paperå·²è¿è¡è³å°?PAPER_CHALLENGE_MIN_DAYS å¤?        - Paperå¤æ® >= PAPER_CHALLENGE_MIN_SHARPE
        """
        if paper_candidate.status != CandidateStatus.PAPER:
            return False, "ææèå¿é¡»å¤äºPAPERç¶æ?
        if running_candidate.status != CandidateStatus.RUNNING:
            return False, "è¢«ææèå¿é¡»å¤äºRUNNINGç¶æ?

        paper_sharpe = paper_candidate.sharpe_paper_5d or 0.0
        running_sharpe = running_candidate.sharpe_test or 0.0

        if paper_sharpe < self.PAPER_CHALLENGE_MIN_SHARPE:
            return False, f"Paperå¤æ® {paper_sharpe:.3f} ä½äºé¨æ§ {self.PAPER_CHALLENGE_MIN_SHARPE}"

        if paper_sharpe <= running_sharpe:
            return False, f"Paperå¤æ® {paper_sharpe:.3f} æªè¶è¿Runningå¤æ® {running_sharpe:.3f}"

        # æ£æ¥Paperè¿è¡å¤©æ°
        paper_days = 0
        if paper_candidate.deployed_at:
            paper_days = (datetime.utcnow() - paper_candidate.deployed_at).days

        if paper_days < self.PAPER_CHALLENGE_MIN_DAYS:
            return False, f"Paperè¿è¡ {paper_days} å¤©ï¼ä¸è¶³ {self.PAPER_CHALLENGE_MIN_DAYS} å¤?

        # éçº§åRunning
        ok1, msg1 = await self.transition(
            candidate=running_candidate,
            target_status=CandidateStatus.DEGRADED,
            reason=f"è¢«Paperææè?{paper_candidate.id} æ¿æ¢",
            db_session=db_session,
            metadata={"challenger_id": paper_candidate.id, "paper_sharpe": paper_sharpe},
        )
        if not ok1:
            return False, f"éçº§åRunningå¤±è´¥: {msg1}"

        # æåPaperå°Running
        ok2, msg2 = await self.transition(
            candidate=paper_candidate,
            target_status=CandidateStatus.RUNNING,
            reason=f"æææåï¼æ¿æ?{running_candidate.id}",
            db_session=db_session,
            metadata={"replaced_id": running_candidate.id, "previous_sharpe": running_sharpe},
        )
        return ok2, msg2

    async def retire(
        self,
        candidate: Candidate,
        reason: str,
        db_session: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """éå½¹åéç­ç¥ã?""
        return await self.transition(
            candidate=candidate,
            target_status=CandidateStatus.RETIRED,
            reason=reason,
            db_session=db_session,
        )

    async def _publish_event(self, event: StateTransitionEvent) -> None:
        """åå¸ç¶æåæ´äºä»¶å°Redisã?""
        if self.redis is None:
            return
        try:
            channel = f"candidate:{event.candidate_id}:state"
            await self.redis.publish(channel, json.dumps(event.to_dict(), ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Redisäºä»¶åå¸å¤±è´¥: {e}")


# ---------------------------------------------------------------------------
# æ¹éç¶æç®¡ç?# ---------------------------------------------------------------------------

class CandidateLifecycleManager:
    """æ¹éåéçå½å¨æç®¡çå¨ã?""

    def __init__(self, state_machine: Optional[CandidateStateMachine] = None) -> None:
        self.sm = state_machine or CandidateStateMachine()

    async def batch_transition(
        self,
        candidates: List[Candidate],
        target_status: CandidateStatus,
        reason: str,
        db_session: Optional[Any] = None,
    ) -> List[Tuple[Candidate, bool, str]]:
        """æ¹éç¶æè½¬æ¢ã?""
        results = []
        for c in candidates:
            ok, msg = await self.sm.transition(c, target_status, reason, db_session)
            results.append((c, ok, msg))
        return results

    async def scan_and_degrade(
        self,
        candidates: List[Candidate],
        drawdown_map: Dict[str, float],
        db_session: Optional[Any] = None,
    ) -> List[Tuple[Candidate, bool, str]]:
        """æ«æå¹¶éçº§åæ¤è¶æ çåéã?""
        results = []
        for c in candidates:
            dd = drawdown_map.get(c.id, 0.0)
            ok, msg = await self.sm.force_degrade_on_drawdown(c, dd, db_session)
            if ok:
                results.append((c, ok, msg))
        return results

    async def scan_regime_mismatch(
        self,
        candidates: List[Candidate],
        regime_map: Dict[str, str],
        strategy_regime_map: Dict[str, str],
        db_session: Optional[Any] = None,
    ) -> List[Tuple[Candidate, bool, str]]:
        """æ«æRegimeä¸å¹éå¹¶éçº§ã?""
        results = []
        for c in candidates:
            current_regime = regime_map.get(c.symbol, "ALL")
            strategy_regime = strategy_regime_map.get(c.id, "ALL")
            ok, msg = await self.sm.pause_on_regime_mismatch(
                c, current_regime, strategy_regime, db_session
            )
            if ok:
                results.append((c, ok, msg))
        return results

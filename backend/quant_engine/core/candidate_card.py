"""
åéç­ç¥å¡ççæå¨

ä¸ºæ¯ä¸ªåéç­ç¥çææ ååä¿¡æ¯å¡çï¼åå«ï¼
- åºç¡ä¿¡æ¯ï¼IDãåç§ãå¬å¼ãç¶æï¼
- ç»©æææ ï¼å¤æ®ãåæ¤ãCalmarç­ï¼
- è¿åä¿¡æ¯ï¼ä»£æ°ãç¶ä»£ãç®å­ï¼
- çå½å¨ææ¶é´çº?- é£é©è¯ä¼°æ ç­¾
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models import Candidate, CandidateStatus


# ---------------------------------------------------------------------------
# å¡çæ°æ®ç»æ
# ---------------------------------------------------------------------------

@dataclass
class PerformanceSnapshot:
    sharpe_train: Optional[float] = None
    sharpe_val: Optional[float] = None
    sharpe_test: Optional[float] = None
    sharpe_paper_5d: Optional[float] = None
    max_drawdown: Optional[float] = None
    calmar: Optional[float] = None
    total_trades: Optional[int] = None
    win_rate: Optional[float] = None
    avg_holding_hours: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sharpe_train": self.sharpe_train,
            "sharpe_val": self.sharpe_val,
            "sharpe_test": self.sharpe_test,
            "sharpe_paper_5d": self.sharpe_paper_5d,
            "max_drawdown": self.max_drawdown,
            "calmar": self.calmar,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "avg_holding_hours": self.avg_holding_hours,
        }


@dataclass
class LifecycleTimeline:
    created_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    degraded_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    retire_reason: Optional[str] = None
    current_status: str = ""
    status_duration_hours: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "degraded_at": self.degraded_at.isoformat() if self.degraded_at else None,
            "retired_at": self.retired_at.isoformat() if self.retired_at else None,
            "retire_reason": self.retire_reason,
            "current_status": self.current_status,
            "status_duration_hours": round(self.status_duration_hours, 2),
        }


@dataclass
class RiskLabel:
    label: str
    level: str  # LOW | MEDIUM | HIGH | CRITICAL
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "level": self.level,
            "description": self.description,
        }


@dataclass
class CandidateCard:
    """åéç­ç¥å®æ´å¡ç?""

    candidate_id: str
    symbol: str
    strategy_type: str
    formula: str
    formula_summary: str = ""
    status: str = ""
    generation: int = 0
    parent_id: Optional[str] = None
    is_seed: bool = False
    seed_code: Optional[str] = None

    performance: PerformanceSnapshot = field(default_factory=PerformanceSnapshot)
    timeline: LifecycleTimeline = field(default_factory=LifecycleTimeline)
    risk_labels: List[RiskLabel] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "strategy_type": self.strategy_type,
            "formula": self.formula,
            "formula_summary": self.formula_summary,
            "status": self.status,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "is_seed": self.is_seed,
            "seed_code": self.seed_code,
            "performance": self.performance.to_dict(),
            "timeline": self.timeline.to_dict(),
            "risk_labels": [r.to_dict() for r in self.risk_labels],
            "tags": self.tags,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# å¡ççæå?# ---------------------------------------------------------------------------

class CandidateCardGenerator:
    """åéç­ç¥å¡ççæå¨"""

    def __init__(self) -> None:
        pass

    def generate(
        self,
        candidate: Candidate,
        lineage_info: Optional[Dict[str, Any]] = None,
        current_drawdown: Optional[float] = None,
    ) -> CandidateCard:
        """
        ä¸ºåéç­ç¥çæå®æ´å¡çã?
        Parameters
        ----------
        candidate : Candidate
            åéç­ç¥ORMå¯¹è±¡
        lineage_info : dict, optional
            è¡ç¼è¿½è¸ªä¿¡æ?        current_drawdown : float, optional
            å½ååæ¤ï¼ç¨äºé£é©æ ç­¾ï¼

        Returns
        -------
        CandidateCard
        """
        perf = self._extract_performance(candidate)
        timeline = self._extract_timeline(candidate)
        risk_labels = self._generate_risk_labels(candidate, current_drawdown)
        tags = self._generate_tags(candidate)
        formula_summary = self._summarize_formula(candidate.formula)

        card = CandidateCard(
            candidate_id=candidate.id,
            symbol=candidate.symbol,
            strategy_type=candidate.strategy_type,
            formula=candidate.formula,
            formula_summary=formula_summary,
            status=candidate.status.value,
            generation=candidate.generation,
            parent_id=candidate.parent_id,
            is_seed=candidate.is_seed,
            seed_code=candidate.seed_code,
            performance=perf,
            timeline=timeline,
            risk_labels=risk_labels,
            tags=tags,
            metadata={
                "lineage": lineage_info or {},
                "params": candidate.params,
                "notes": candidate.notes,
            },
        )
        return card

    def _extract_performance(self, candidate: Candidate) -> PerformanceSnapshot:
        return PerformanceSnapshot(
            sharpe_train=candidate.sharpe_train,
            sharpe_val=candidate.sharpe_val,
            sharpe_test=candidate.sharpe_test,
            sharpe_paper_5d=candidate.sharpe_paper_5d,
            max_drawdown=candidate.max_drawdown,
            calmar=candidate.calmar,
            total_trades=candidate.total_trades,
            win_rate=candidate.win_rate,
            avg_holding_hours=candidate.avg_holding_hours,
        )

    def _extract_timeline(self, candidate: Candidate) -> LifecycleTimeline:
        now = datetime.utcnow()
        duration = 0.0
        if candidate.status == CandidateStatus.RUNNING and candidate.deployed_at:
            duration = (now - candidate.deployed_at).total_seconds() / 3600
        elif candidate.status == CandidateStatus.DEGRADED and candidate.degraded_at:
            duration = (now - candidate.degraded_at).total_seconds() / 3600
        elif candidate.status == CandidateStatus.RETIRED and candidate.retired_at:
            duration = (now - candidate.retired_at).total_seconds() / 3600
        elif candidate.created_at:
            duration = (now - candidate.created_at).total_seconds() / 3600

        return LifecycleTimeline(
            created_at=candidate.created_at,
            deployed_at=candidate.deployed_at,
            degraded_at=candidate.degraded_at,
            retired_at=candidate.retired_at,
            retire_reason=candidate.retire_reason,
            current_status=candidate.status.value,
            status_duration_hours=duration,
        )

    def _generate_risk_labels(
        self,
        candidate: Candidate,
        current_drawdown: Optional[float] = None,
    ) -> List[RiskLabel]:
        labels: List[RiskLabel] = []

        dd = current_drawdown if current_drawdown is not None else (candidate.max_drawdown or 0.0)
        if dd > 0.15:
            labels.append(RiskLabel("é«åæ?, "CRITICAL", f"æå¤§åæ?{dd:.1%}ï¼è¶åºå®å¨èå?))
        elif dd > 0.08:
            labels.append(RiskLabel("ä¸­é«åæ¤", "HIGH", f"æå¤§åæ?{dd:.1%}ï¼éå³æ³¨"))
        elif dd > 0.05:
            labels.append(RiskLabel("ä¸­ç­åæ¤", "MEDIUM", f"æå¤§åæ?{dd:.1%}"))

        sharpe = candidate.sharpe_test or 0.0
        if sharpe < 0.3:
            labels.append(RiskLabel("ä½å¤æ?, "HIGH", f"æµè¯å¤æ® {sharpe:.2f}ï¼ç­ç¥ç¨³å¥æ§ä¸è¶?))
        elif sharpe < 0.6:
            labels.append(RiskLabel("å¤æ®åä½", "MEDIUM", f"æµè¯å¤æ® {sharpe:.2f}"))

        if candidate.total_trades and candidate.total_trades < 20:
            labels.append(RiskLabel("äº¤ææ¬¡æ°å°?, "MEDIUM", f"ä»?{candidate.total_trades} ç¬äº¤æï¼ç»è®¡æä¹æé"))

        win_rate = candidate.win_rate or 0.0
        if win_rate < 0.35:
            labels.append(RiskLabel("ä½èç?, "HIGH", f"èç {win_rate:.1%}ï¼çäºæ¯éè¶³å¤é«?))

        return labels

    def _generate_tags(self, candidate: Candidate) -> List[str]:
        tags: List[str] = []

        if candidate.is_seed:
            tags.append("ç§å­ç­ç¥")
        else:
            tags.append("è¿åç­ç¥")

        if candidate.generation == 0:
            tags.append("åä»£")
        elif candidate.generation <= 10:
            tags.append("æ©æä»£æ°")
        else:
            tags.append(f"G{candidate.generation}")

        sharpe = candidate.sharpe_test or 0.0
        if sharpe > 1.5:
            tags.append("é«å¤æ?)
        elif sharpe > 1.0:
            tags.append("è¯å¤æ?)

        if candidate.status == CandidateStatus.RUNNING:
            tags.append("å®çè¿è¡")
        elif candidate.status == CandidateStatus.PAPER:
            tags.append("æ¨¡æéªè¯")
        elif candidate.status == CandidateStatus.DEGRADED:
            tags.append("å·²éçº?)

        return tags

    def _summarize_formula(self, formula: str, max_len: int = 80) -> str:
        if len(formula) <= max_len:
            return formula
        return formula[: max_len - 3] + "..."

    def generate_batch(
        self,
        candidates: List[Candidate],
        drawdown_map: Optional[Dict[str, float]] = None,
        lineage_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[CandidateCard]:
        """æ¹éçæåéå¡çã?""
        cards = []
        for c in candidates:
            dd = drawdown_map.get(c.id) if drawdown_map else None
            lineage = lineage_map.get(c.id) if lineage_map else None
            cards.append(self.generate(c, lineage, dd))
        return cards

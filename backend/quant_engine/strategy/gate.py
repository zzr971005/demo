"""
ç­ç¥åå¥é¨ç¦ â?åéç­ç¥è¿å¥å®çåçå¤éæ£éª?

æ£éªé¡¹ï¼?
- PBO/DSR/BH-FDR ç»è®¡æ£éª?
- åæµå¤æ® > 0.6
- æ¨¡æç?2 å¨éªè¯?
- WFE æ ·æ¬å¤ä¿æç
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.models import Candidate, CandidateStatus
from app.config import get_settings
from validation.pbo_dsr import (
    ValidationReport,
    bh_fdr_sharpe,
    dsr,
    full_validation,
    pbo_cscv,
    wfe,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# é¨ç¦æ£éªç»æ?
# ---------------------------------------------------------------------------

@dataclass
class GateCheckResult:
    """åé¡¹æ£éªç»æ?""

    name: str
    passed: bool
    value: Any
    threshold: Any
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }


@dataclass
class GateReport:
    """é¨ç¦å®æ´æ¥å"""

    candidate_id: str
    symbol: str
    overall_passed: bool
    checks: List[GateCheckResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "symbol": self.symbol,
            "overall_passed": self.overall_passed,
            "checks": [c.to_dict() for c in self.checks],
            "timestamp": self.timestamp.isoformat(),
            "recommendation": self.recommendation,
        }


# ---------------------------------------------------------------------------
# ç­ç¥é¨ç¦
# ---------------------------------------------------------------------------

class StrategyGate:
    """
    ç­ç¥åå¥é¨ç¦

    ææåéç­ç¥å¨è¿å¥PAPERæRUNNINGç¶æåå¿é¡»éè¿æ­¤é¨ç¦æ£éªã?
    """

    DEFAULT_CONFIG = {
        "min_backtest_sharpe": 0.6,
        "min_paper_sharpe": 0.5,
        "min_paper_days": 10,
        "max_pbo": 0.5,
        "min_dsr_prob": 0.95,
        "min_wfe_return": 0.5,
        "bh_fdr_alpha": 0.05,
        "min_total_trades": 20,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.cfg = {**self.DEFAULT_CONFIG, **(config or {})}
        settings = get_settings()
        if settings.system and settings.system.evolution.stages:
            stage_cfg = settings.system.evolution.stages[-1]
            if stage_cfg.min_test_sharpe is not None:
                self.cfg["min_backtest_sharpe"] = stage_cfg.min_test_sharpe

    def check_backtest_sharpe(
        self,
        candidate: Candidate,
        use_test_sharpe: bool = True,
    ) -> GateCheckResult:
        """æ£éªåæµå¤æ®æ¯çã?""
        sharpe = candidate.sharpe_test if use_test_sharpe else candidate.sharpe_val
        threshold = self.cfg["min_backtest_sharpe"]

        if sharpe is None:
            return GateCheckResult(
                name="åæµå¤æ®",
                passed=False,
                value=None,
                threshold=threshold,
                message="åæµå¤æ®æ°æ®ç¼ºå¤±",
            )

        passed = sharpe >= threshold
        return GateCheckResult(
            name="åæµå¤æ®",
            passed=passed,
            value=round(sharpe, 3),
            threshold=threshold,
            message=f"åæµå¤æ® {sharpe:.3f} {'â? if passed else '<'} é¨æ§ {threshold}",
        )

    def check_pbo(
        self,
        validation_report: Optional[ValidationReport] = None,
        all_strategy_returns: Optional[np.ndarray] = None,
    ) -> GateCheckResult:
        """æ£éª?PBOï¼åæµè¿æåæ¦çï¼ã?""
        threshold = self.cfg["max_pbo"]

        if validation_report is not None:
            pbo = validation_report.pbo
        elif all_strategy_returns is not None:
            pbo_result = pbo_cscv(all_strategy_returns, n_splits=4)
            pbo = pbo_result.pbo
        else:
            return GateCheckResult(
                name="PBOæ£éª?,
                passed=False,
                value=None,
                threshold=threshold,
                message="PBOæ°æ®ç¼ºå¤±ï¼éæä¾validation_reportæall_strategy_returnsï¼?,
            )

        passed = pbo < threshold
        return GateCheckResult(
            name="PBOæ£éª?,
            passed=passed,
            value=round(pbo, 3),
            threshold=threshold,
            message=f"PBO={pbo:.3f} {'<' if passed else 'â?} é¨æ§ {threshold}",
        )

    def check_dsr(
        self,
        validation_report: Optional[ValidationReport] = None,
        sharpe: Optional[float] = None,
        n_trials: int = 1,
    ) -> GateCheckResult:
        """æ£éª?DSRï¼æ¾æ°å¤æ®æ¯çï¼ã?""
        threshold = self.cfg["min_dsr_prob"]

        if validation_report is not None:
            dsr_prob = validation_report.dsr_prob
        elif sharpe is not None:
            dsr_prob = dsr(sharpe, n_trials)
        else:
            return GateCheckResult(
                name="DSRæ£éª?,
                passed=False,
                value=None,
                threshold=threshold,
                message="DSRæ°æ®ç¼ºå¤±",
            )

        passed = dsr_prob > threshold
        return GateCheckResult(
            name="DSRæ£éª?,
            passed=passed,
            value=round(dsr_prob, 3),
            threshold=threshold,
            message=f"DSRæ¦ç={dsr_prob:.3f} {'>' if passed else 'â?} é¨æ§ {threshold}",
        )

    def check_bh_fdr(
        self,
        validation_report: Optional[ValidationReport] = None,
        all_strategy_sharpes: Optional[np.ndarray] = None,
    ) -> GateCheckResult:
        """æ£éª?BH-FDRï¼Benjamini-Hochberg å¨æé¨æ§ï¼ã?""
        if validation_report is not None:
            bh_sig = validation_report.bh_significant
        elif all_strategy_sharpes is not None:
            significant, _, _ = bh_fdr_sharpe(all_strategy_sharpes)
            bh_sig = significant[-1] if len(significant) > 0 else False
        else:
            return GateCheckResult(
                name="BH-FDRæ£éª?,
                passed=False,
                value=None,
                threshold=True,
                message="BH-FDRæ°æ®ç¼ºå¤±",
            )

        return GateCheckResult(
            name="BH-FDRæ£éª?,
            passed=bh_sig,
            value=bh_sig,
            threshold=True,
            message="éè¿BH-FDRæ¾èæ§æ£éª? if bh_sig else "æªéè¿BH-FDRæ¾èæ§æ£éª?,
        )

    def check_wfe(
        self,
        validation_report: Optional[ValidationReport] = None,
        in_sample_returns: Optional[np.ndarray] = None,
        out_of_sample_returns: Optional[np.ndarray] = None,
    ) -> GateCheckResult:
        """æ£éª?WFEï¼Walk-Forward Efficiencyï¼ã?""
        threshold = self.cfg["min_wfe_return"]

        if validation_report is not None:
            wfe_ret = validation_report.wfe_return
        elif in_sample_returns is not None and out_of_sample_returns is not None:
            wfe_result = wfe(in_sample_returns, out_of_sample_returns)
            wfe_ret = wfe_result["wfe_return"]
        else:
            return GateCheckResult(
                name="WFEæ£éª?,
                passed=False,
                value=None,
                threshold=threshold,
                message="WFEæ°æ®ç¼ºå¤±",
            )

        passed = wfe_ret > threshold
        return GateCheckResult(
            name="WFEæ£éª?,
            passed=passed,
            value=round(wfe_ret, 3),
            threshold=threshold,
            message=f"WFEæ¶çä¿æç?{wfe_ret:.3f} {'>' if passed else 'â?} é¨æ§ {threshold}",
        )

    def check_paper_validation(
        self,
        candidate: Candidate,
        paper_sharpe: Optional[float] = None,
        paper_start_date: Optional[datetime] = None,
    ) -> GateCheckResult:
        """æ£éªæ¨¡æçéªè¯ï¼è³å°?å¨ï¼ã?""
        min_days = self.cfg["min_paper_days"]
        min_sharpe = self.cfg["min_paper_sharpe"]

        if candidate.status == CandidateStatus.PAPER and paper_start_date is None:
            paper_start_date = candidate.deployed_at

        if paper_start_date is None:
            return GateCheckResult(
                name="æ¨¡æçéªè¯?,
                passed=False,
                value=None,
                threshold=f"{min_days}å¤?,
                message="æ¨¡æçå¼å§æ¥æç¼ºå¤?,
            )

        paper_days = (datetime.utcnow() - paper_start_date).days
        if paper_days < min_days:
            return GateCheckResult(
                name="æ¨¡æçéªè¯?,
                passed=False,
                value=f"{paper_days}å¤?,
                threshold=f"{min_days}å¤?,
                message=f"æ¨¡æçä»è¿è¡ {paper_days} å¤©ï¼ä¸è¶³ {min_days} å¤?,
            )

        sharpe = paper_sharpe or candidate.sharpe_paper_5d or 0.0
        if sharpe < min_sharpe:
            return GateCheckResult(
                name="æ¨¡æçéªè¯?,
                passed=False,
                value=round(sharpe, 3),
                threshold=min_sharpe,
                message=f"æ¨¡æçå¤æ?{sharpe:.3f} ä½äºé¨æ§ {min_sharpe}",
            )

        return GateCheckResult(
            name="æ¨¡æçéªè¯?,
            passed=True,
            value=f"{paper_days}å¤? å¤æ®{sharpe:.3f}",
            threshold=f"{min_days}å¤? å¤æ®{min_sharpe}",
            message=f"æ¨¡æçéªè¯éè¿ï¼è¿è¡?{paper_days} å¤©ï¼å¤æ® {sharpe:.3f}",
        )

    def check_trade_count(
        self,
        candidate: Candidate,
    ) -> GateCheckResult:
        """æ£éªäº¤ææ¬¡æ°æ¯å¦è¶³å¤ã?""
        threshold = self.cfg["min_total_trades"]
        trades = candidate.total_trades or 0

        passed = trades >= threshold
        return GateCheckResult(
            name="äº¤ææ¬¡æ°",
            passed=passed,
            value=trades,
            threshold=threshold,
            message=f"äº¤ææ¬¡æ° {trades} {'â? if passed else '<'} é¨æ§ {threshold}",
        )

    def full_check(
        self,
        candidate: Candidate,
        validation_report: Optional[ValidationReport] = None,
        all_strategy_returns: Optional[np.ndarray] = None,
        in_sample_returns: Optional[np.ndarray] = None,
        out_of_sample_returns: Optional[np.ndarray] = None,
        paper_sharpe: Optional[float] = None,
        paper_start_date: Optional[datetime] = None,
    ) -> GateReport:
        """
        æ§è¡å®æ´é¨ç¦æ£éªã?

        Parameters
        ----------
        candidate : Candidate
            åéç­ç?
        validation_report : ValidationReport, optional
            é¢è®¡ç®çç»è®¡æ£éªæ¥å?
        all_strategy_returns : np.ndarray, optional
            ææç­ç¥æ¶çç©é?(n_periods, n_strategies)ï¼ç¨äºPBO
        in_sample_returns : np.ndarray, optional
            æ ·æ¬åæ¶ç?
        out_of_sample_returns : np.ndarray, optional
            æ ·æ¬å¤æ¶ç?
        paper_sharpe : float, optional
            æ¨¡æçå¤æ?
        paper_start_date : datetime, optional
            æ¨¡æçå¼å§æ¥æ?

        Returns
        -------
        GateReport
        """
        checks: List[GateCheckResult] = []

        # 1. åæµå¤æ®
        checks.append(self.check_backtest_sharpe(candidate))

        # 2. PBO
        checks.append(self.check_pbo(validation_report, all_strategy_returns))

        # 3. DSR
        sharpe = candidate.sharpe_test or candidate.sharpe_val or 0.0
        checks.append(self.check_dsr(validation_report, sharpe, n_trials=1))

        # 4. BH-FDR
        checks.append(self.check_bh_fdr(validation_report))

        # 5. WFE
        checks.append(self.check_wfe(validation_report, in_sample_returns, out_of_sample_returns))

        # 6. æ¨¡æçéªè¯ï¼PAPERç¶ææéè¦ï¼
        if candidate.status in (CandidateStatus.PAPER, CandidateStatus.DEPLOYABLE):
            checks.append(self.check_paper_validation(candidate, paper_sharpe, paper_start_date))

        # 7. äº¤ææ¬¡æ°
        checks.append(self.check_trade_count(candidate))

        all_passed = all(c.passed for c in checks)

        recommendation = "éè¿" if all_passed else "æªéè¿ï¼?
        if not all_passed:
            failed = [c.name for c in checks if not c.passed]
            recommendation += f" {', '.join(failed)} æ£éªå¤±è´?

        return GateReport(
            candidate_id=candidate.id,
            symbol=candidate.symbol,
            overall_passed=all_passed,
            checks=checks,
            recommendation=recommendation,
        )

    def can_promote_to_paper(self, candidate: Candidate) -> Tuple[bool, str]:
        """æ£æ¥åéæ¯å¦å¯ä»¥æåå°PAPERç¶æã?""
        report = self.full_check(candidate)
        # æåPAPERåªéè¦åæµéè¿
        backtest_ok = any(c.name == "åæµå¤æ®" and c.passed for c in report.checks)
        pbo_ok = any(c.name == "PBOæ£éª? and c.passed for c in report.checks)

        if not backtest_ok:
            return False, "åæµå¤æ®æªè¾¾æ ?
        if not pbo_ok:
            return False, "PBOæ£éªæªéè¿"
        return True, "å¯ä»¥æåå°PAPER"

    def can_promote_to_running(self, candidate: Candidate) -> Tuple[bool, str]:
        """æ£æ¥åéæ¯å¦å¯ä»¥æåå°RUNNINGç¶æã?""
        report = self.full_check(candidate)
        if not report.overall_passed:
            return False, report.recommendation
        return True, "æææ£éªéè¿ï¼å¯ä»¥æåå°RUNNING"


# ---------------------------------------------------------------------------
# ä¾¿æ·å½æ°
# ---------------------------------------------------------------------------

def check_candidate_gate(
    candidate: Candidate,
    validation_report: Optional[ValidationReport] = None,
    **kwargs: Any,
) -> GateReport:
    """ä¾¿æ·å½æ°ï¼å¯¹åéç­ç¥æ§è¡å®æ´é¨ç¦æ£éªã?""
    gate = StrategyGate()
    return gate.full_check(candidate, validation_report=validation_report, **kwargs)

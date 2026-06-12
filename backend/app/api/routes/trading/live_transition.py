"""
实盘衔接 API - 模拟盘 → 实盘 转换门控

paper→live 升级需通过一组硬门槛（设计文档 §6）：
  1. 模拟盘观察期 ≥ min_paper_days（默认 7 天）
  2. 属该品种 top2（is_selected_strategy 且 strategy_rank ∈ {1,2}）
  3. DSR > 0
  4. PBO ≤ max_pbo（默认 0.5）
  5. 模拟盘夏普 vs 回测夏普 偏差 ≤ max_sharpe_dev（默认 5%）
  6. 与已上线策略 |相关性| < tau_corr（默认 0.5）

数据缺失（如尚无模拟盘观察）时对应门槛判为未通过——保守拦截，绝不放行。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.db import get_session
from app.models import Candidate, LiveTransitionCandidate
from quant_engine.analysis.strategy_correlation import StrategyCorrelationService

router = APIRouter(prefix="/api/live-transition", tags=["live-transition"])

# 门控默认参数
MIN_PAPER_DAYS = 7
MAX_PBO = 0.5
MAX_SHARPE_DEV = 0.05
TAU_CORR = 0.5


def _evaluation_period_days(c: LiveTransitionCandidate) -> Optional[int]:
    if c.paper_test_start and c.paper_test_end:
        return (c.paper_test_end - c.paper_test_start).days
    return None


def _candidate_to_dict(c: LiveTransitionCandidate) -> Dict[str, Any]:
    """Serialize a candidate using the real model columns."""
    is_live = c.live_start is not None
    return {
        "strategy_id": c.candidate_id,
        "symbol": c.symbol,
        "transition_status": c.transition_status,
        "transition_score": c.transition_score,
        "evaluation_period_days": _evaluation_period_days(c),
        "current_metrics": {
            "sharpe": c.live_sharpe if is_live else c.paper_sharpe,
            "return": c.live_return if is_live else c.paper_return,
            "drawdown": c.live_max_dd if is_live else c.paper_max_dd,
        },
        "paper_metrics": {
            "sharpe": c.paper_sharpe,
            "return": c.paper_return,
            "drawdown": c.paper_max_dd,
        },
        "is_ready": c.transition_status in ("approved", "completed"),
        "promoted_at": c.live_start.isoformat() if c.live_start else None,
    }


def _check(name: str, passed: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def evaluate_live_gate(
    session,
    ltc: LiveTransitionCandidate,
    candidate: Optional[Candidate],
) -> Dict[str, Any]:
    """评估 paper→live 门控，返回 {allowed, checks}。"""
    checks: List[Dict[str, Any]] = []

    # 1) 观察期
    days = _evaluation_period_days(ltc)
    checks.append(
        _check(
            "模拟盘观察期",
            days is not None and days >= MIN_PAPER_DAYS,
            f"观察 {days} 天（需 ≥ {MIN_PAPER_DAYS}）"
            if days is not None
            else "尚无模拟盘观察记录",
        )
    )

    # 2) 属该品种 top2
    is_top2 = bool(
        candidate
        and candidate.is_selected_strategy
        and candidate.strategy_rank in (1, 2)
    )
    checks.append(
        _check(
            "属该品种 top2",
            is_top2,
            f"strategy_rank={getattr(candidate, 'strategy_rank', None)}"
            if candidate
            else "候选库中未找到该策略",
        )
    )

    # 3) DSR > 0
    dsr_val = getattr(candidate, "dsr", None) if candidate else None
    checks.append(
        _check(
            "DSR > 0",
            dsr_val is not None and dsr_val > 0,
            f"DSR={dsr_val}" if dsr_val is not None else "DSR 未计算",
        )
    )

    # 4) PBO ≤ 阈值
    pbo_val = getattr(candidate, "pbo", None) if candidate else None
    checks.append(
        _check(
            "PBO 达标",
            pbo_val is not None and pbo_val <= MAX_PBO,
            f"PBO={pbo_val}（需 ≤ {MAX_PBO}）"
            if pbo_val is not None
            else "PBO 未计算",
        )
    )

    # 5) 模拟盘 vs 回测 夏普偏差
    bt_sharpe = None
    if candidate:
        bt_sharpe = candidate.sharpe_test or candidate.sharpe_train
    paper_sharpe = ltc.paper_sharpe
    if paper_sharpe is not None and bt_sharpe:
        dev = abs(paper_sharpe - bt_sharpe) / (abs(bt_sharpe) + 1e-9)
        checks.append(
            _check(
                "模拟/回测夏普一致",
                dev <= MAX_SHARPE_DEV,
                f"偏差 {dev:.1%}（需 ≤ {MAX_SHARPE_DEV:.0%}）",
            )
        )
    else:
        checks.append(
            _check("模拟/回测夏普一致", False, "缺少模拟盘或回测夏普")
        )

    # 6) 与已上线策略低相关
    corr_detail = "无已上线策略，跳过"
    corr_ok = True
    if candidate and candidate.formula and candidate.symbol:
        live_rows = (
            session.query(Candidate)
            .filter(
                Candidate.deployed_at.isnot(None),
                Candidate.id != candidate.id,
                Candidate.formula.isnot(None),
            )
            .all()
        )
        if live_rows:
            svc = StrategyCorrelationService()
            target = svc.compute_return_series(candidate.formula, candidate.symbol)
            if target is None:
                corr_ok = False
                corr_detail = "无法重建该策略收益序列"
            else:
                max_abs = 0.0
                worst = None
                import numpy as np

                for lr in live_rows:
                    ls = svc.compute_return_series(lr.formula, lr.symbol)
                    if ls is None:
                        continue
                    joined = target.to_frame("a").join(
                        ls.to_frame("b"), how="inner"
                    ).dropna()
                    if joined.shape[0] < 30:
                        continue
                    rho = float(
                        np.corrcoef(joined["a"], joined["b"])[0, 1]
                    )
                    if abs(rho) > max_abs:
                        max_abs, worst = abs(rho), lr.id
                corr_ok = max_abs < TAU_CORR
                corr_detail = (
                    f"与已上线策略最大|相关|={max_abs:.3f}"
                    f"（{worst}），需 < {TAU_CORR}"
                )
    checks.append(_check("与已上线策略低相关", corr_ok, corr_detail))

    allowed = all(c["passed"] for c in checks)
    return {"allowed": allowed, "checks": checks}


class TransitionRequest(BaseModel):
    strategy_id: str
    target_mode: str  # simulation -> live
    force: bool = False  # 跳过门控强制升级（仅供测试/人工复核）


@router.get("/candidates")
async def get_transition_candidates() -> Dict[str, Any]:
    """获取可过渡到实盘的候选策略"""
    with get_session() as session:
        query = select(LiveTransitionCandidate)
        result = session.execute(query)
        candidates = result.scalars().all()

        return {
            "candidates": [_candidate_to_dict(c) for c in candidates]
        }


@router.get("/strategies/{strategy_id}/gate")
async def get_live_gate(strategy_id: str) -> Dict[str, Any]:
    """评估某策略的 paper→live 门控（只读，不升级）。"""
    with get_session() as session:
        ltc = session.execute(
            select(LiveTransitionCandidate).where(
                LiveTransitionCandidate.candidate_id == strategy_id
            )
        ).scalar_one_or_none()
        if not ltc:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy {strategy_id} not found in candidates",
            )
        candidate = session.get(Candidate, strategy_id)
        gate = evaluate_live_gate(session, ltc, candidate)
        return {"strategy_id": strategy_id, **gate}


@router.post("/strategies/{strategy_id}/promote")
async def promote_to_live(
    strategy_id: str,
    request: TransitionRequest,
) -> Dict[str, Any]:
    """将策略升级到实盘（需通过门控，除非 force=True）。"""
    with get_session() as session:
        candidate_ltc = session.execute(
            select(LiveTransitionCandidate).where(
                LiveTransitionCandidate.candidate_id == strategy_id
            )
        ).scalar_one_or_none()

        if not candidate_ltc:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy {strategy_id} not found in candidates",
            )

        candidate = session.get(Candidate, strategy_id)
        gate = evaluate_live_gate(session, candidate_ltc, candidate)

        if not gate["allowed"] and not request.force:
            failed = [c for c in gate["checks"] if not c["passed"]]
            return {
                "strategy_id": strategy_id,
                "status": "BLOCKED",
                "allowed": False,
                "failed_checks": failed,
                "checks": gate["checks"],
            }

        candidate_ltc.transition_status = "completed"
        candidate_ltc.live_start = datetime.utcnow()
        if candidate is not None:
            candidate.deployed_at = candidate_ltc.live_start
        session.commit()

        return {
            "strategy_id": strategy_id,
            "status": "PROMOTED",
            "allowed": True,
            "forced": request.force and not gate["allowed"],
            "promoted_at": candidate_ltc.live_start.isoformat(),
            "checks": gate["checks"],
        }


@router.get("/strategies/{strategy_id}/evaluation")
async def get_transition_evaluation(strategy_id: str) -> Dict[str, Any]:
    """获取过渡评估"""
    with get_session() as session:
        query = select(LiveTransitionCandidate).where(
            LiveTransitionCandidate.candidate_id == strategy_id
        )
        result = session.execute(query)
        candidate = result.scalar_one_or_none()

        if candidate:
            return _candidate_to_dict(candidate)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy {strategy_id} not found in candidates",
            )

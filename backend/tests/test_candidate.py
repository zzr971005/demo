"""
候选策略状态机测试

覆盖:
- 合法状态流转
- 非法状态流转拒绝
- 回撤强制降级
- Regime不匹配暂停
- Paper挑战Running
- 批量状态管理
- 事件发布
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest

from backend.app.models import Candidate, CandidateStatus
from backend.quant_engine.core.candidate_core import (
    CandidateLifecycleManager,
    CandidateStateMachine,
    StateTransitionEvent,
)


class MockCandidate:
    """内存中的候选策略模拟对象"""

    def __init__(self, candidate_id: str, symbol: str, status: CandidateStatus) -> None:
        self.id = candidate_id
        self.symbol = symbol
        self.status = status
        self.updated_at = datetime.utcnow()
        self.deployed_at: datetime | None = None
        self.degraded_at: datetime | None = None
        self.retired_at: datetime | None = None
        self.retire_reason: str | None = None
        self.sharpe_paper_5d: float | None = None
        self.sharpe_test: float | None = None


class TestStateTransitions:
    """状态流转测试"""

    @pytest.fixture
    def sm(self) -> CandidateStateMachine:
        return CandidateStateMachine(redis_client=None)

    @pytest.fixture
    def seed_candidate(self) -> MockCandidate:
        return MockCandidate("cand-001", "RB", CandidateStatus.SEED)

    @pytest.fixture
    def running_candidate(self) -> MockCandidate:
        c = MockCandidate("cand-002", "RB", CandidateStatus.RUNNING)
        c.deployed_at = datetime.utcnow() - timedelta(days=5)
        return c

    def test_seed_to_backtest(self, sm: CandidateStateMachine, seed_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(sm.transition(seed_candidate, CandidateStatus.BACKTEST))
        assert ok
        assert seed_candidate.status == CandidateStatus.BACKTEST

    def test_seed_to_paper_invalid(self, sm: CandidateStateMachine, seed_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(sm.transition(seed_candidate, CandidateStatus.PAPER))
        assert not ok
        assert "非法状态流转" in msg
        assert seed_candidate.status == CandidateStatus.SEED

    def test_running_to_retired(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(sm.transition(running_candidate, CandidateStatus.RETIRED, reason="测试退役"))
        assert ok
        assert running_candidate.status == CandidateStatus.RETIRED
        assert running_candidate.retired_at is not None
        assert running_candidate.retire_reason == "测试退役"

    def test_retired_no_transition(self, sm: CandidateStateMachine) -> None:
        retired = MockCandidate("cand-003", "RB", CandidateStatus.RETIRED)
        ok, msg = asyncio.run(sm.transition(retired, CandidateStatus.RUNNING))
        assert not ok
        assert retired.status == CandidateStatus.RETIRED

    def test_same_state_noop(self, sm: CandidateStateMachine, seed_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(sm.transition(seed_candidate, CandidateStatus.SEED))
        assert ok  # 同状态转换应该是合法的

    def test_get_allowed_transitions(self, sm: CandidateStateMachine) -> None:
        allowed = sm.get_allowed_transitions(CandidateStatus.SEED)
        assert CandidateStatus.BACKTEST in allowed
        assert CandidateStatus.RETIRED in allowed
        assert CandidateStatus.RUNNING not in allowed


class TestForceDegrade:
    """回撤强制降级测试"""

    @pytest.fixture
    def sm(self) -> CandidateStateMachine:
        return CandidateStateMachine(redis_client=None)

    @pytest.fixture
    def running_candidate(self) -> MockCandidate:
        c = MockCandidate("cand-004", "RB", CandidateStatus.RUNNING)
        c.deployed_at = datetime.utcnow() - timedelta(days=5)
        return c

    def test_degrade_on_high_drawdown(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(sm.force_degrade_on_drawdown(running_candidate, 0.10))
        assert ok
        assert running_candidate.status == CandidateStatus.DEGRADED
        assert running_candidate.degraded_at is not None

    def test_no_degrade_on_low_drawdown(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(sm.force_degrade_on_drawdown(running_candidate, 0.05))
        assert not ok
        assert running_candidate.status == CandidateStatus.RUNNING

    def test_degrade_threshold_exact(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        # 刚好等于阈值不应降级
        ok, msg = asyncio.run(sm.force_degrade_on_drawdown(running_candidate, 0.08))
        assert not ok

    def test_degrade_only_for_active_states(self, sm: CandidateStateMachine) -> None:
        seed = MockCandidate("cand-005", "RB", CandidateStatus.SEED)
        ok, msg = asyncio.run(sm.force_degrade_on_drawdown(seed, 0.10))
        assert not ok
        assert "不支持回撤降级" in msg


class TestRegimeMismatch:
    """Regime不匹配暂停测试"""

    @pytest.fixture
    def sm(self) -> CandidateStateMachine:
        return CandidateStateMachine(redis_client=None)

    @pytest.fixture
    def running_candidate(self) -> MockCandidate:
        return MockCandidate("cand-006", "RB", CandidateStatus.RUNNING)

    def test_mismatch_degrades(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(
            sm.pause_on_regime_mismatch(running_candidate, "TREND", "BAND")
        )
        assert ok
        assert running_candidate.status == CandidateStatus.DEGRADED

    def test_match_no_action(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(
            sm.pause_on_regime_mismatch(running_candidate, "TREND", "TREND")
        )
        assert not ok
        assert "Regime匹配" in msg
        assert running_candidate.status == CandidateStatus.RUNNING

    def test_all_regime_no_action(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(
            sm.pause_on_regime_mismatch(running_candidate, "TREND", "ALL")
        )
        assert not ok
        assert "Regime匹配" in msg

    def test_non_running_no_action(self, sm: CandidateStateMachine) -> None:
        paper = MockCandidate("cand-007", "RB", CandidateStatus.PAPER)
        ok, msg = asyncio.run(
            sm.pause_on_regime_mismatch(paper, "TREND", "BAND")
        )
        assert not ok
        assert "只有RUNNING状态" in msg


class TestPaperChallenge:
    """Paper挑战Running测试"""

    @pytest.fixture
    def sm(self) -> CandidateStateMachine:
        return CandidateStateMachine(redis_client=None)

    @pytest.fixture
    def running_candidate(self) -> MockCandidate:
        c = MockCandidate("cand-008", "RB", CandidateStatus.RUNNING)
        c.sharpe_test = 0.8
        return c

    @pytest.fixture
    def paper_candidate(self) -> MockCandidate:
        c = MockCandidate("cand-009", "RB", CandidateStatus.PAPER)
        c.sharpe_paper_5d = 1.2
        c.deployed_at = datetime.utcnow() - timedelta(days=15)
        return c

    def test_successful_challenge(self, sm: CandidateStateMachine, paper_candidate: MockCandidate, running_candidate: MockCandidate) -> None:
        ok, msg = asyncio.run(
            sm.auto_paper_challenge(paper_candidate, running_candidate)
        )
        assert ok
        assert running_candidate.status == CandidateStatus.DEGRADED
        assert paper_candidate.status == CandidateStatus.RUNNING

    def test_paper_not_paper_status_fails(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        not_paper = MockCandidate("cand-010", "RB", CandidateStatus.BACKTEST)
        ok, msg = asyncio.run(
            sm.auto_paper_challenge(not_paper, running_candidate)
        )
        assert not ok
        assert "挑战者必须处于PAPER状态" in msg

    def test_running_not_running_fails(self, sm: CandidateStateMachine, paper_candidate: MockCandidate) -> None:
        not_running = MockCandidate("cand-011", "RB", CandidateStatus.PAPER)
        ok, msg = asyncio.run(
            sm.auto_paper_challenge(paper_candidate, not_running)
        )
        assert not ok
        assert "被挑战者必须处于RUNNING状态" in msg

    def test_low_sharpe_fails(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        weak_paper = MockCandidate("cand-012", "RB", CandidateStatus.PAPER)
        weak_paper.sharpe_paper_5d = 0.3
        weak_paper.deployed_at = datetime.utcnow() - timedelta(days=15)
        ok, msg = asyncio.run(
            sm.auto_paper_challenge(weak_paper, running_candidate)
        )
        assert not ok
        assert "低于门槛" in msg

    def test_insufficient_days_fails(self, sm: CandidateStateMachine, running_candidate: MockCandidate) -> None:
        new_paper = MockCandidate("cand-013", "RB", CandidateStatus.PAPER)
        new_paper.sharpe_paper_5d = 1.5
        new_paper.deployed_at = datetime.utcnow() - timedelta(days=3)
        ok, msg = asyncio.run(
            sm.auto_paper_challenge(new_paper, running_candidate)
        )
        assert not ok
        assert "不足" in msg


class TestLifecycleManager:
    """批量生命周期管理测试"""

    @pytest.fixture
    def manager(self) -> CandidateLifecycleManager:
        return CandidateLifecycleManager()

    def test_batch_transition(self, manager: CandidateLifecycleManager) -> None:
        candidates = [
            MockCandidate(f"cand-{i:03d}", "RB", CandidateStatus.SEED)
            for i in range(3)
        ]
        results = asyncio.run(
            manager.batch_transition(candidates, CandidateStatus.BACKTEST, "批量测试")
        )
        assert len(results) == 3
        for c, ok, msg in results:
            assert ok
            assert c.status == CandidateStatus.BACKTEST

    def test_scan_and_degrade(self, manager: CandidateLifecycleManager) -> None:
        candidates = [
            MockCandidate("cand-100", "RB", CandidateStatus.RUNNING),
            MockCandidate("cand-101", "MA", CandidateStatus.RUNNING),
            MockCandidate("cand-102", "AU", CandidateStatus.PAPER),
        ]
        drawdown_map = {
            "cand-100": 0.10,  # 超标
            "cand-101": 0.05,  # 未超标
            "cand-102": 0.12,  # 超标
        }
        results = asyncio.run(
            manager.scan_and_degrade(candidates, drawdown_map)
        )
        assert len(results) == 2  # 只有 2 个超标
        degraded_ids = {c.id for c, ok, msg in results if ok}
        assert "cand-100" in degraded_ids
        assert "cand-102" in degraded_ids

    def test_scan_regime_mismatch(self, manager: CandidateLifecycleManager) -> None:
        candidates = [
            MockCandidate("cand-200", "RB", CandidateStatus.RUNNING),
            MockCandidate("cand-201", "MA", CandidateStatus.RUNNING),
        ]
        regime_map = {"RB": "TREND", "MA": "BAND"}
        strategy_regime_map = {"cand-200": "BAND", "cand-201": "BAND"}
        results = asyncio.run(
            manager.scan_regime_mismatch(candidates, regime_map, strategy_regime_map)
        )
        assert len(results) == 1  # 只有 RB 不匹配
        assert results[0][0].id == "cand-200"


class TestStateTransitionEvent:
    """状态变更事件测试"""

    def test_event_to_dict(self) -> None:
        event = StateTransitionEvent(
            candidate_id="cand-test",
            symbol="RB",
            from_status=CandidateStatus.SEED,
            to_status=CandidateStatus.BACKTEST,
            triggered_at=datetime(2024, 1, 1, 12, 0, 0),
            reason="测试",
            metadata={"test": True},
        )
        d = event.to_dict()
        assert d["candidate_id"] == "cand-test"
        assert d["symbol"] == "RB"
        assert d["from_status"] == "SEED"
        assert d["to_status"] == "BACKTEST"
        assert d["reason"] == "测试"
        assert d["metadata"]["test"] is True

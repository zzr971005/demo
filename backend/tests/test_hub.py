"""
数据接入层测试 — TimescaleDB 读写、SQLite 读写、数据管道

注意：运行测试需要本地 PostgreSQL + TimescaleDB 服务已启动
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.quant_engine.data.hub import TimescaleHub, SQLiteHub, DataPipeline, OHLCVRecord, FactorRecord


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_ohlcv_df():
    """生成测试用的OHLCV数据"""
    n = 100
    dates = pd.date_range(start="2024-01-01", periods=n, freq="H", tz="UTC")
    prices = np.cumsum(np.random.randn(n) * 2) + 100

    return pd.DataFrame(
        {
            "open": prices + np.random.randn(n) * 0.5,
            "high": prices + np.abs(np.random.randn(n)) * 2,
            "low": prices - np.abs(np.random.randn(n)) * 2,
            "close": prices + np.random.randn(n) * 0.5,
            "volume": np.random.randint(1000, 10000, n),
            "open_interest": np.random.randint(5000, 50000, n),
        },
        index=dates,
    )


@pytest.fixture
def sample_factor_series():
    """生成测试用的因子值序列"""
    n = 100
    dates = pd.date_range(start="2024-01-01", periods=n, freq="H", tz="UTC")
    values = np.random.randn(n)
    return pd.Series(values, index=dates, name="test_factor")


# ---------------------------------------------------------------------------
# TimescaleHub 测试
# ---------------------------------------------------------------------------

class TestTimescaleHub:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.hub = TimescaleHub()

    def test_insert_and_query_ohlcv(self, sample_ohlcv_df):
        # 插入数据
        inserted = self.hub.insert_ohlcv(
            symbol="RB_TEST",
            df=sample_ohlcv_df,
            duration_seconds=3600,
            if_exists="replace",
        )
        assert inserted == len(sample_ohlcv_df)

        # 查询数据
        result = self.hub.query_ohlcv(
            symbol="RB_TEST",
            duration_seconds=3600,
        )

        assert not result.empty
        assert len(result) == len(sample_ohlcv_df)
        assert "open" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns

    def test_query_ohlcv_with_date_range(self, sample_ohlcv_df):
        self.hub.insert_ohlcv(
            symbol="RB_TEST",
            df=sample_ohlcv_df,
            duration_seconds=3600,
            if_exists="replace",
        )

        start_dt = sample_ohlcv_df.index[10]
        end_dt = sample_ohlcv_df.index[50]

        result = self.hub.query_ohlcv(
            symbol="RB_TEST",
            start_dt=start_dt,
            end_dt=end_dt,
            duration_seconds=3600,
        )

        assert len(result) == 41

    def test_get_available_range(self, sample_ohlcv_df):
        self.hub.insert_ohlcv(
            symbol="RB_TEST",
            df=sample_ohlcv_df,
            duration_seconds=3600,
            if_exists="replace",
        )

        min_ts, max_ts = self.hub.get_available_range("RB_TEST", 3600)

        assert min_ts is not None
        assert max_ts is not None
        assert min_ts == sample_ohlcv_df.index[0].to_pydatetime()
        assert max_ts == sample_ohlcv_df.index[-1].to_pydatetime()

    def test_get_all_symbols(self, sample_ohlcv_df):
        self.hub.insert_ohlcv(
            symbol="RB_TEST",
            df=sample_ohlcv_df,
            duration_seconds=3600,
            if_exists="replace",
        )
        self.hub.insert_ohlcv(
            symbol="MA_TEST",
            df=sample_ohlcv_df,
            duration_seconds=3600,
            if_exists="replace",
        )

        symbols = self.hub.get_all_symbols(3600)

        assert "RB_TEST" in symbols
        assert "MA_TEST" in symbols

    def test_insert_and_query_factors(self, sample_factor_series):
        inserted = self.hub.insert_factors(
            symbol="RB_TEST",
            factor_name="test_factor",
            values=sample_factor_series,
            generation=1,
            candidate_id="test_candidate_001",
            if_exists="replace",
        )
        assert inserted == len(sample_factor_series)

        # 查询单个因子
        result = self.hub.query_factors(
            symbol="RB_TEST",
            factor_name="test_factor",
        )

        assert not result.empty
        assert len(result) == len(sample_factor_series)
        assert "test_factor" in result.columns

    def test_query_multiple_factors(self, sample_factor_series):
        # 插入两个不同的因子
        self.hub.insert_factors(
            symbol="RB_TEST",
            factor_name="factor_a",
            values=sample_factor_series,
            if_exists="replace",
        )
        self.hub.insert_factors(
            symbol="RB_TEST",
            factor_name="factor_b",
            values=sample_factor_series * 2,
            if_exists="replace",
        )

        result = self.hub.query_factors(
            symbol="RB_TEST",
            factor_name=["factor_a", "factor_b"],
        )

        assert not result.empty
        assert "factor_a" in result.columns
        assert "factor_b" in result.columns


# ---------------------------------------------------------------------------
# SQLiteHub 测试
# ---------------------------------------------------------------------------

class TestSQLiteHub:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.temp_db = tempfile.mktemp(suffix=".db")
        self.hub = SQLiteHub(self.temp_db)

    def test_insert_and_query_candidate(self):
        candidate = {
            "id": "test_candidate_001",
            "symbol": "RB",
            "status": "SEED",
            "regime": "TREND",
            "formula": "ts_mean(close, 20) / ts_mean(close, 60)",
            "params": None,
            "parent_id": None,
            "generation": 0,
            "is_seed": True,
            "seed_code": "S01",
            "notes": "测试策略",
        }

        cid = self.hub.insert_candidate(candidate)
        assert cid == "test_candidate_001"

        candidates = self.hub.query_candidates(symbol="RB", status="SEED")
        assert len(candidates) == 1
        assert candidates[0]["id"] == "test_candidate_001"
        assert candidates[0]["formula"] == "ts_mean(close, 20) / ts_mean(close, 60)"

    def test_update_candidate_metrics(self):
        candidate = {
            "id": "test_candidate_002",
            "symbol": "RB",
            "status": "SEED",
            "regime": "TREND",
            "formula": "zscore(close, 20)",
            "params": None,
            "parent_id": None,
            "generation": 1,
            "is_seed": False,
            "seed_code": None,
            "notes": None,
        }
        self.hub.insert_candidate(candidate)

        self.hub.update_candidate_metrics(
            candidate_id="test_candidate_002",
            metrics={
                "sharpe_train": 1.5,
                "sharpe_val": 1.2,
                "sharpe_test": 1.0,
                "max_drawdown": 0.08,
                "calmar": 12.5,
                "win_rate": 0.55,
                "profit_factor": 1.8,
                "total_trades": 100,
                "avg_holding_bars": 4.5,
            },
        )

        candidates = self.hub.query_candidates(symbol="RB")
        assert len(candidates) == 1
        assert candidates[0]["sharpe_train"] == 1.5
        assert candidates[0]["max_drawdown"] == 0.08
        assert candidates[0]["win_rate"] == 0.55

    def test_update_candidate_status(self):
        candidate = {
            "id": "test_candidate_003",
            "symbol": "RB",
            "status": "SEED",
            "regime": "TREND",
            "formula": "ts_return(close, 10)",
            "params": None,
            "parent_id": None,
            "generation": 2,
            "is_seed": False,
            "seed_code": None,
            "notes": None,
        }
        self.hub.insert_candidate(candidate)

        self.hub.update_candidate_status(
            candidate_id="test_candidate_003",
            status="BACKTEST",
        )

        candidates = self.hub.query_candidates(status="BACKTEST")
        assert len(candidates) == 1
        assert candidates[0]["status"] == "BACKTEST"

    def test_symbol_switch(self):
        # 设置模式
        self.hub.set_symbol_mode("RB", "PAPER", reason="测试模拟盘", operator="system")
        self.hub.set_symbol_mode("MA", "LIVE", reason="实盘测试", operator="admin")

        # 获取单个
        mode = self.hub.get_symbol_mode("RB")
        assert mode == "PAPER"

        # 获取所有
        modes = self.hub.get_all_symbol_modes()
        assert modes["RB"] == "PAPER"
        assert modes["MA"] == "LIVE"

    def test_trade_records(self):
        trade = {
            "id": "trade_001",
            "symbol": "RB",
            "candidate_id": "test_candidate_001",
            "side": "BUY",
            "quantity": 1,
            "entry_price": 3500.0,
            "exit_price": None,
            "entry_at": datetime.now(),
            "exit_at": None,
            "status": "PENDING",
            "pnl": None,
            "pnl_pct": None,
            "commission": 0.0,
            "slippage": 0.0,
            "is_paper": True,
            "order_id": None,
            "notes": "测试交易",
        }

        tid = self.hub.insert_trade(trade)
        assert tid == "trade_001"

        # 更新平仓信息
        self.hub.update_trade_exit(
            trade_id="trade_001",
            exit_price=3600.0,
            exit_at=datetime.now() + timedelta(hours=5),
            pnl=1000.0,
            pnl_pct=0.0286,
            status="FILLED",
        )


# ---------------------------------------------------------------------------
# OHLCVRecord 和 FactorRecord 测试
# ---------------------------------------------------------------------------

class TestDataRecords:

    def test_ohlcv_record_to_dict(self):
        record = OHLCVRecord(
            symbol="RB",
            ts=datetime.now(),
            open=3500.0,
            high=3550.0,
            low=3480.0,
            close=3520.0,
            volume=10000.0,
            open_interest=50000.0,
        )
        d = record.to_dict()
        assert d["symbol"] == "RB"
        assert d["open"] == 3500.0
        assert d["close"] == 3520.0

    def test_factor_record_to_dict(self):
        record = FactorRecord(
            symbol="RB",
            ts=datetime.now(),
            factor_name="test_factor",
            value=0.5,
            generation=1,
            candidate_id="test_001",
        )
        d = record.to_dict()
        assert d["symbol"] == "RB"
        assert d["factor_name"] == "test_factor"
        assert d["value"] == 0.5
        assert d["generation"] == 1


# ---------------------------------------------------------------------------
# 数据管道测试（模拟数据）
# ---------------------------------------------------------------------------

class TestDataPipeline:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.timescale_hub = TimescaleHub()

    def test_pipeline_initialization(self):
        pipeline = DataPipeline(timescale_hub=self.timescale_hub)
        assert pipeline is not None
        assert pipeline.timescale is not None

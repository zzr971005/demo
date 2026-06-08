"""
手续费模型 — 分层手续费与滑点

支持：
- 不同品种不同费率
- IF平今手续费是隔日的10倍
- 滑点模型（固定tick / 百分比 / 波动率自适应）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class FuturesFeeConfig:
    """期货品种手续费配置"""

    symbol: str
    open_rate: float  # 开仓手续费率
    close_rate: float  # 平仓手续费率（隔日）
    close_today_rate: float  # 平今手续费率
    min_fee: float = 0.0  # 最低手续费
    is_percent: bool = True  # True=比例费率, False=固定金额（元/手）

    @property
    def close_today_multiplier(self) -> float:
        """平今费率相对于平仓费率的倍数"""
        if self.close_rate > 0:
            return self.close_today_rate / self.close_rate
        return 1.0


@dataclass
class SlippageConfig:
    """滑点配置"""

    mode: str = "fixed"  # fixed / percent / volatility
    fixed_ticks: float = 1.0  # 固定tick数
    percent: float = 0.0001  # 百分比模式：万分之一
    vol_window: int = 20  # 波动率自适应窗口
    vol_multiplier: float = 0.1  # 波动率乘数


# ---------------------------------------------------------------------------
# 默认费率表（与 system.yaml 对齐）
# ---------------------------------------------------------------------------

DEFAULT_FEE_TABLE: Dict[str, FuturesFeeConfig] = {
    # 低保证金品种
    "MA": FuturesFeeConfig("MA", 0.0001, 0.0001, 0.0001),
    "RB": FuturesFeeConfig("RB", 0.0001, 0.0001, 0.0001),
    "M": FuturesFeeConfig("M", 0.0001, 0.0001, 0.0001),
    "TA": FuturesFeeConfig("TA", 0.0001, 0.0001, 0.0001),
    "FG": FuturesFeeConfig("FG", 0.0001, 0.0001, 0.0001),
    "SR": FuturesFeeConfig("SR", 0.0001, 0.0001, 0.0001),
    "SA": FuturesFeeConfig("SA", 0.0001, 0.0001, 0.0001),
    "PP": FuturesFeeConfig("PP", 0.0001, 0.0001, 0.0001),
    # 高保证金品种
    "AU": FuturesFeeConfig("AU", 0.0001, 0.0001, 0.0001),
    "CU": FuturesFeeConfig("CU", 0.0001, 0.0001, 0.0001),
    "SC": FuturesFeeConfig("SC", 0.0001, 0.0001, 0.0001),
    # IF 特殊费率：平今是隔日的10倍
    "IF": FuturesFeeConfig("IF", 0.000023, 0.000023, 0.00023),
    "IC": FuturesFeeConfig("IC", 0.000023, 0.000023, 0.00023),
    "IH": FuturesFeeConfig("IH", 0.000023, 0.000023, 0.00023),
}


# ---------------------------------------------------------------------------
# 手续费模型
# ---------------------------------------------------------------------------

class FeeModel:
    """
    期货手续费模型

    支持分层费率查询、IF平今特殊处理、滑点计算。
    """

    def __init__(
        self,
        fee_table: Optional[Dict[str, FuturesFeeConfig]] = None,
        slippage: Optional[SlippageConfig] = None,
    ):
        self.fee_table = fee_table or DEFAULT_FEE_TABLE.copy()
        self.slippage = slippage or SlippageConfig()

    def get_config(self, symbol: str) -> FuturesFeeConfig:
        """获取品种手续费配置（找不到返回默认）"""
        return self.fee_table.get(symbol, FuturesFeeConfig(symbol, 0.0001, 0.0001, 0.0001))

    def set_config(self, symbol: str, config: FuturesFeeConfig) -> None:
        """设置品种手续费配置"""
        self.fee_table[symbol] = config

    def calculate_fee(
        self,
        symbol: str,
        price: float,
        lots: int,
        contract_value_per_lot: float,
        action: str = "open",
        is_close_today: bool = False,
    ) -> float:
        """
        计算单笔手续费

        Parameters
        ----------
        symbol : str
            品种代码
        price : float
            成交价格
        lots : int
            手数
        contract_value_per_lot : float
            每手合约名义价值
        action : str
            'open' / 'close'
        is_close_today : bool
            是否平今

        Returns
        -------
        float — 手续费金额
        """
        cfg = self.get_config(symbol)

        if action == "open":
            rate = cfg.open_rate
        elif is_close_today:
            rate = cfg.close_today_rate
        else:
            rate = cfg.close_rate

        if cfg.is_percent:
            fee = lots * contract_value_per_lot * rate
        else:
            fee = lots * rate

        return max(fee, cfg.min_fee)

    def calculate_slippage(
        self,
        price: np.ndarray,
        tick_size: float = 1.0,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        计算滑点金额

        Parameters
        ----------
        price : np.ndarray
            价格序列
        tick_size : float
            最小变动价位
        high, low : np.ndarray, optional
            高低价序列（波动率自适应模式需要）

        Returns
        -------
        np.ndarray — 滑点金额序列
        """
        if self.slippage.mode == "fixed":
            return np.full_like(price, self.slippage.fixed_ticks * tick_size, dtype=np.float64)

        elif self.slippage.mode == "percent":
            return price * self.slippage.percent

        elif self.slippage.mode == "volatility":
            if high is None or low is None:
                # 没有高低价时退化为固定模式
                return np.full_like(price, self.slippage.fixed_ticks * tick_size, dtype=np.float64)
            tr = high - low
            vol = np.empty_like(tr)
            w = self.slippage.vol_window
            for i in range(len(tr)):
                if i < w - 1:
                    vol[i] = tr[i]
                else:
                    s = 0.0
                    for j in range(i - w + 1, i + 1):
                        s += tr[j]
                    vol[i] = s / w
            return vol * self.slippage.vol_multiplier

        else:
            return np.full_like(price, self.slippage.fixed_ticks * tick_size, dtype=np.float64)

    def total_cost(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        lots: int,
        contract_value_per_lot: float,
        is_close_today: bool = False,
        slippage_ticks: float = 1.0,
        tick_size: float = 1.0,
    ) -> Dict[str, float]:
        """
        计算一笔完整交易的全部成本

        Returns
        -------
        dict — {open_fee, close_fee, slippage_cost, total_cost}
        """
        open_fee = self.calculate_fee(symbol, entry_price, lots, contract_value_per_lot, "open")
        close_fee = self.calculate_fee(symbol, exit_price, lots, contract_value_per_lot, "close", is_close_today)
        slippage_cost = slippage_ticks * tick_size * lots * 2  # 开平均有滑点
        total = open_fee + close_fee + slippage_cost
        return {
            "open_fee": open_fee,
            "close_fee": close_fee,
            "slippage_cost": slippage_cost,
            "total_cost": total,
        }

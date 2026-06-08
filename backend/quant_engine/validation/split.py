"""
样本切分 — 严格时序分离

支持：
- 训练/验证/测试 6个月/6个月/6个月滑动窗口
- T-1截断（严禁未来函数）
- Walk-Forward 支持
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TimeSplit:
    """时序切分结果"""

    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    val_start: pd.Timestamp
    val_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    fold: int = 0


@dataclass
class WalkForwardSplit:
    """Walk-Forward 切分结果"""

    splits: List[TimeSplit]

    def __iter__(self) -> Iterator[TimeSplit]:
        return iter(self.splits)

    def __len__(self) -> int:
        return len(self.splits)

    def __getitem__(self, idx: int) -> TimeSplit:
        return self.splits[idx]


# ---------------------------------------------------------------------------
# 核心切分逻辑
# ---------------------------------------------------------------------------

class TemporalSplitter:
    """
    严格时序样本切分器

    严禁未来函数：所有标签和特征只能使用 T-1 及之前的数据。
    """

    def __init__(
        self,
        train_months: int = 6,
        val_months: int = 6,
        test_months: int = 6,
        min_train_months: int = 3,
        gap_bars: int = 1,  # T-1 截断：训练集和验证集之间至少间隔1根K线
    ):
        self.train_months = train_months
        self.val_months = val_months
        self.test_months = test_months
        self.min_train_months = min_train_months
        self.gap_bars = gap_bars

    def split(
        self,
        index: Union[pd.DatetimeIndex, pd.Index, np.ndarray],
        n_splits: int = 1,
        stride_months: Optional[int] = None,
    ) -> WalkForwardSplit:
        """
        生成时序切分

        Parameters
        ----------
        index : DatetimeIndex or array
            时间索引
        n_splits : int
            Walk-Forward 切分次数，1=单次切分
        stride_months : int, optional
            滑动步长（月），默认等于 test_months

        Returns
        -------
        WalkForwardSplit
        """
        if isinstance(index, np.ndarray):
            index = pd.DatetimeIndex(index)
        elif not isinstance(index, pd.DatetimeIndex):
            index = pd.DatetimeIndex(index)

        if len(index) == 0:
            return WalkForwardSplit(splits=[])

        stride = stride_months or self.test_months
        splits: List[TimeSplit] = []

        total_window_months = self.train_months + self.val_months + self.test_months
        start_ts = index[0]
        end_ts = index[-1]

        for fold in range(n_splits):
            offset_months = fold * stride

            train_start = start_ts
            train_end = start_ts + pd.DateOffset(months=self.train_months + offset_months)
            val_start = train_end + pd.DateOffset(hours=self.gap_bars)  # T-1 截断
            val_end = val_start + pd.DateOffset(months=self.val_months)
            test_start = val_end + pd.DateOffset(hours=self.gap_bars)  # T-1 截断
            test_end = test_start + pd.DateOffset(months=self.test_months)

            if test_end > end_ts:
                break

            train_mask = (index >= train_start) & (index < train_end)
            val_mask = (index >= val_start) & (index < val_end)
            test_mask = (index >= test_start) & (index < test_end)

            train_idx = np.where(train_mask)[0]
            val_idx = np.where(val_mask)[0]
            test_idx = np.where(test_mask)[0]

            if len(train_idx) < self.min_train_months * 30 * 5:  # 粗略估计：每月约5*30根1H K线
                continue

            splits.append(TimeSplit(
                train_idx=train_idx,
                val_idx=val_idx,
                test_idx=test_idx,
                train_start=train_start,
                train_end=train_end,
                val_start=val_start,
                val_end=val_end,
                test_start=test_start,
                test_end=test_end,
                fold=fold,
            ))

        return WalkForwardSplit(splits=splits)

    def split_by_bars(
        self,
        n_bars: int,
        n_splits: int = 1,
        stride_bars: Optional[int] = None,
    ) -> WalkForwardSplit:
        """
        按K线数切分（不依赖时间索引）

        Parameters
        ----------
        n_bars : int
            总K线数
        n_splits : int
            Walk-Forward 切分次数
        stride_bars : int, optional
            滑动步长（K线数），默认等于 test 长度

        Returns
        -------
        WalkForwardSplit
        """
        train_bars = self.train_months * 30 * 5  # 6月 ≈ 900根1H
        val_bars = self.val_months * 30 * 5
        test_bars = self.test_months * 30 * 5
        stride = stride_bars or test_bars

        splits: List[TimeSplit] = []
        dummy_index = pd.date_range("2020-01-01", periods=n_bars, freq="H")

        for fold in range(n_splits):
            offset = fold * stride

            t0 = 0
            t1 = train_bars + offset
            t2 = t1 + self.gap_bars
            t3 = t2 + val_bars
            t4 = t3 + self.gap_bars
            t5 = t4 + test_bars

            if t5 > n_bars:
                break

            splits.append(TimeSplit(
                train_idx=np.arange(t0, t1),
                val_idx=np.arange(t2, t3),
                test_idx=np.arange(t4, t5),
                train_start=dummy_index[t0],
                train_end=dummy_index[t1],
                val_start=dummy_index[t2],
                val_end=dummy_index[t3],
                test_start=dummy_index[t4],
                test_end=dummy_index[t5],
                fold=fold,
            ))

        return WalkForwardSplit(splits=splits)

    def split_purged_kfold(
        self,
        index: pd.DatetimeIndex,
        n_splits: int = 5,
        embargo_pct: float = 0.01,
    ) -> WalkForwardSplit:
        """
        Purged K-Fold 切分（带清除和禁运区）

        参考 Lopez de Prado《Advances in Financial Machine Learning》

        Parameters
        ----------
        index : DatetimeIndex
        n_splits : int
        embargo_pct : float
            禁运区比例（防止信息泄漏）

        Returns
        -------
        WalkForwardSplit
        """
        n = len(index)
        fold_size = n // n_splits
        embargo_size = max(1, int(fold_size * embargo_pct))
        splits: List[TimeSplit] = []

        for i in range(n_splits):
            test_start = i * fold_size
            test_end = min((i + 1) * fold_size, n)

            # 训练集 = 测试集之前，但清除掉与测试集相邻的部分
            train_end = max(0, test_start - embargo_size)
            train_idx = np.arange(0, train_end)

            # 验证集 = 测试集之后的一小部分（可选）
            val_start = min(n, test_end + embargo_size)
            val_end = min(n, val_start + fold_size // 2)
            val_idx = np.arange(val_start, val_end) if val_start < val_end else np.array([], dtype=int)

            test_idx = np.arange(test_start, test_end)

            splits.append(TimeSplit(
                train_idx=train_idx,
                val_idx=val_idx,
                test_idx=test_idx,
                train_start=index[0] if len(train_idx) > 0 else index[0],
                train_end=index[train_end - 1] if train_end > 0 else index[0],
                val_start=index[val_start] if len(val_idx) > 0 else index[-1],
                val_end=index[val_end - 1] if val_end > val_start else index[-1],
                test_start=index[test_start],
                test_end=index[test_end - 1],
                fold=i,
            ))

        return WalkForwardSplit(splits=splits)


# ---------------------------------------------------------------------------
# 数据对齐工具（防止未来函数）
# ---------------------------------------------------------------------------

def align_features_labels(
    features: pd.DataFrame,
    labels: pd.Series,
    lookahead: int = 1,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    特征与标签对齐：标签向前移动 lookahead 期，确保特征只用 T-1 及之前信息

    Parameters
    ----------
    features : pd.DataFrame
        特征矩阵（T时刻已知）
    labels : pd.Series
        标签序列（T时刻的未来收益）
    lookahead : int
        前瞻期数

    Returns
    -------
    (aligned_features, aligned_labels)
    """
    aligned_labels = labels.shift(-lookahead)
    mask = aligned_labels.notna()
    return features[mask].copy(), aligned_labels[mask].copy()


def purge_overlap(
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    gap: int = 1,
) -> np.ndarray:
    """
    从训练集中清除与测试集重叠或相邻的索引

    Parameters
    ----------
    train_idx : np.ndarray
    test_idx : np.ndarray
    gap : int
        清除间隔

    Returns
    -------
    np.ndarray — 清除后的训练集索引
    """
    if len(test_idx) == 0:
        return train_idx
    test_min = test_idx.min()
    test_max = test_idx.max()
    mask = (train_idx < test_min - gap) | (train_idx > test_max + gap)
    return train_idx[mask]


def embargo(
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    embargo_pct: float = 0.01,
) -> np.ndarray:
    """
    在训练集尾部设置禁运区（防止信息泄漏到验证/测试集）

    Parameters
    ----------
    train_idx : np.ndarray
    test_idx : np.ndarray
    embargo_pct : float
        禁运区占训练集比例

    Returns
    -------
    np.ndarray — 禁运后的训练集索引
    """
    if len(train_idx) == 0 or len(test_idx) == 0:
        return train_idx
    embargo_size = max(1, int(len(train_idx) * embargo_pct))
    # 移除训练集末尾 embargo_size 个样本
    return train_idx[:-embargo_size] if len(train_idx) > embargo_size else train_idx

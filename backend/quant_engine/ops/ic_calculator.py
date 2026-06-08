"""
IC计算模块
批量计算因子的IC指标
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from scipy import stats
from sqlalchemy import select

from app.db import get_session
from app.models import Candidate, CandidateStatus, FactorValueHistory, ValidationPipelineData
from quant_engine.data.hub import TimescaleHub

logger = logging.getLogger(__name__)


class ICCalculator:
    """IC计算器"""

    def __init__(self, timescale_hub: TimescaleHub):
        self.timescale_hub = timescale_hub

    def calculate_ic_batch(
        self,
        symbol: str,
        generation: int
    ) -> Dict[str, Any]:
        """
        批量计算IC指标

        Args:
            symbol: 品种
            generation: 代数

        Returns:
            统计信息字典
        """
        logger.info(f"开始批量计算IC: {symbol} 第{generation}代")

        # 获取通过Demo筛选的因子
        with get_session() as session:
            result = session.execute(
                select(Candidate).where(
                    Candidate.symbol == symbol,
                    Candidate.generation == generation,
                    Candidate.status == CandidateStatus.APPROVED
                )
            )
            candidates = result.scalars().all()

        if not candidates:
            logger.warning(f"没有找到通过Demo筛选的因子: {symbol} 第{generation}代")
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "top_50": []
            }

        logger.info(f"找到 {len(candidates)} 个通过Demo筛选的因子")

        # 加载价格数据
        price_data = self._load_price_data(symbol)
        if price_data is None:
            logger.error(f"无法加载价格数据: {symbol}")
            return {
                "total": len(candidates),
                "success": 0,
                "failed": len(candidates),
                "top_50": []
            }

        # 计算每个因子的IC指标
        ic_results = []
        success_count = 0
        failed_count = 0

        for candidate in candidates:
            try:
                ic_metrics = self._calculate_single_factor_ic(
                    candidate,
                    price_data,
                    symbol
                )
                ic_results.append({
                    "candidate": candidate,
                    "ic_metrics": ic_metrics
                })
                success_count += 1
                logger.debug(f"成功计算IC: {candidate.id}")
            except Exception as e:
                failed_count += 1
                logger.error(f"计算IC失败: {candidate.id}, 错误: {e}")

        # 按IC综合评分排序
        ic_results.sort(
            key=lambda x: self._calculate_ic_composite_score(x["ic_metrics"]),
            reverse=True
        )

        # 筛选前50个
        top_50 = ic_results[:50]

        # 保存IC指标到数据库
        for result in top_50:
            self._save_ic_metrics(
                result["candidate"],
                result["ic_metrics"]
            )

        logger.info(
            f"IC计算完成: 总数={len(candidates)}, "
            f"成功={success_count}, 失败={failed_count}, "
            f"前50个={len(top_50)}"
        )

        # 更新ValidationPipelineData表
        self._update_validation_pipeline_data(
            symbol,
            generation,
            len(candidates),
            len(top_50)
        )

        return {
            "total": len(candidates),
            "success": success_count,
            "failed": failed_count,
            "top_50": [r["candidate"].id for r in top_50]
        }

    def _load_price_data(self, symbol: str) -> Dict[str, np.ndarray]:
        """加载价格数据"""
        try:
            df = self.timescale_hub.get_ohlcv(
                symbol=symbol,
                duration_seconds=3600  # 1H数据
            )

            if df is None or df.empty:
                logger.error(f"价格数据为空: {symbol}")
                return None

            return {
                "open": df["open"].values,
                "high": df["high"].values,
                "low": df["low"].values,
                "close": df["close"].values,
                "volume": df["volume"].values,
                "timestamp": df.index.values
            }
        except Exception as e:
            logger.error(f"加载价格数据失败: {symbol}, 错误: {e}")
            return None

    def _calculate_single_factor_ic(
        self,
        candidate: Candidate,
        price_data: Dict[str, np.ndarray],
        symbol: str
    ) -> Dict[str, Any]:
        """
        计算单个因子的IC指标

        Args:
            candidate: 候选因子
            price_data: 价格数据
            symbol: 品种

        Returns:
            IC指标字典
        """
        # 加载因子值序列
        factor_values = self._load_factor_values(candidate.id, symbol)
        if factor_values is None:
            raise ValueError(f"无法加载因子值序列: {candidate.id}")

        # 计算未来收益
        future_returns = self._calculate_future_returns(price_data)

        # 计算多窗口IC
        windows = [4, 24, 168]  # 4h, 24h, 168h
        ic_metrics = {}

        for window in windows:
            ic_mean, ic_std, ic_ir = self._calculate_ic_window(
                factor_values,
                future_returns,
                window
            )
            ic_metrics[f"ic_mean_{window}h"] = ic_mean
            ic_metrics[f"ic_std_{window}h"] = ic_std
            ic_metrics[f"ic_ir_{window}h"] = ic_ir

        # 计算IC半衰期
        ic_half_life = self._calculate_ic_half_life(
            factor_values,
            future_returns
        )
        ic_metrics["ic_half_life"] = ic_half_life

        return ic_metrics

    def _load_factor_values(
        self,
        factor_id: str,
        symbol: str
    ) -> np.ndarray:
        """加载因子值序列"""
        with get_session() as session:
            result = session.execute(
                select(FactorValueHistory).where(
                    FactorValueHistory.factor_id == factor_id,
                    FactorValueHistory.symbol == symbol
                ).order_by(FactorValueHistory.timestamp)
            )
            records = result.scalars().all()

        if not records:
            return None

        return np.array([r.factor_value for r in records])

    def _calculate_future_returns(
        self,
        price_data: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """计算未来收益"""
        close = price_data["close"]
        # 计算对数收益率
        returns = np.log(close[1:] / close[:-1])
        # 填充第一个值为0
        returns = np.concatenate([[0], returns])
        return returns

    def _calculate_ic_window(
        self,
        factor_values: np.ndarray,
        future_returns: np.ndarray,
        window: int
    ) -> Tuple[float, float, float]:
        """
        计算单窗口IC

        Args:
            factor_values: 因子值序列
            future_returns: 未来收益序列
            window: 时间窗口

        Returns:
            (IC均值, IC标准差, IC信息比率)
        """
        # 确保长度一致
        min_len = min(len(factor_values), len(future_returns))
        factor_values = factor_values[:min_len]
        future_returns = future_returns[:min_len]

        # 计算滚动IC
        ic_values = []
        for i in range(window, min_len):
            factor_window = factor_values[i-window:i]
            return_window = future_returns[i-window:i]

            # 计算Pearson相关系数
            if len(factor_window) > 1 and len(return_window) > 1:
                ic, _ = stats.pearsonr(factor_window, return_window)
                if not np.isnan(ic):
                    ic_values.append(ic)

        if not ic_values:
            return 0.0, 0.0, 0.0

        ic_mean = np.mean(ic_values)
        ic_std = np.std(ic_values)
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0.0

        return ic_mean, ic_std, ic_ir

    def _calculate_ic_half_life(
        self,
        factor_values: np.ndarray,
        future_returns: np.ndarray
    ) -> float:
        """
        计算IC半衰期

        Args:
            factor_values: 因子值序列
            future_returns: 未来收益序列

        Returns:
            IC半衰期（小时）
        """
        # 计算不同窗口的IC
        windows = [4, 8, 24, 48, 168, 336]
        ic_values = []

        for window in windows:
            ic_mean, _, _ = self._calculate_ic_window(
                factor_values,
                future_returns,
                window
            )
            ic_values.append((window, ic_mean))

        # 找到IC衰减到一半的窗口
        max_ic = max(ic_values, key=lambda x: x[1])[1]
        if max_ic == 0:
            return 0.0

        half_ic = max_ic / 2
        for window, ic in sorted(ic_values):
            if ic <= half_ic:
                return float(window)

        return float(windows[-1])

    def _calculate_ic_composite_score(
        self,
        ic_metrics: Dict[str, Any]
    ) -> float:
        """
        计算IC综合评分

        Args:
            ic_metrics: IC指标字典

        Returns:
            综合评分
        """
        # 加权平均多窗口IC
        weights = {4: 0.3, 24: 0.5, 168: 0.2}
        weighted_ic = 0.0
        for window, weight in weights.items():
            ic_mean = ic_metrics.get(f"ic_mean_{window}h", 0.0)
            weighted_ic += ic_mean * weight

        # IC信息比率
        ic_ir = ic_metrics.get("ic_ir_24h", 0.0)

        # IC半衰期（越长越稳定）
        ic_half_life = ic_metrics.get("ic_half_life", 0.0)
        stability_score = min(ic_half_life / 168.0, 1.0)  # 归一化到[0,1]

        # 综合评分
        composite_score = weighted_ic * 0.6 + ic_ir * 0.2 + stability_score * 0.2

        return composite_score

    def _save_ic_metrics(
        self,
        candidate: Candidate,
        ic_metrics: Dict[str, Any]
    ) -> None:
        """保存IC指标到数据库"""
        with get_session() as session:
            # 更新Candidate表的IC字段
            candidate.ic_mean_4h = ic_metrics.get("ic_mean_4h")
            candidate.ic_mean_24h = ic_metrics.get("ic_mean_24h")
            candidate.ic_mean_168h = ic_metrics.get("ic_mean_168h")
            candidate.ic_ir = ic_metrics.get("ic_ir_24h")
            candidate.ic_half_life = ic_metrics.get("ic_half_life")

    def _update_validation_pipeline_data(
        self,
        symbol: str,
        generation: int,
        total_count: int,
        top_50_count: int
    ) -> None:
        """更新ValidationPipelineData表"""
        with get_session() as session:
            result = session.execute(
                select(ValidationPipelineData).where(
                    ValidationPipelineData.symbol == symbol,
                    ValidationPipelineData.generation == generation
                )
            )
            pipeline_data = result.scalar_one_or_none()

            if pipeline_data:
                pipeline_data.ic_input = total_count
                pipeline_data.ic_output = top_50_count
                pipeline_data.ic_drop = total_count - top_50_count

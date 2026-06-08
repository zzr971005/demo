"""
因子值序列生成模块
对通过Demo筛选的因子生成因子值序列，供IC计算使用
"""

import logging
from typing import List, Dict, Any
import numpy as np
from sqlalchemy import select

from app.db import get_session
from app.models import Candidate, CandidateStatus
from quant_engine.data.hub import TimescaleHub

logger = logging.getLogger(__name__)


class FactorValueGenerator:
    """因子值序列生成器"""

    def __init__(self, timescale_hub: TimescaleHub):
        self.timescale_hub = timescale_hub

    def generate_factor_values(
        self,
        symbol: str,
        generation: int
    ) -> Dict[str, Any]:
        """
        生成因子值序列

        Args:
            symbol: 品种
            generation: 代数

        Returns:
            统计信息字典
        """
        logger.info(f"开始生成因子值序列: {symbol} 第{generation}代")

        # 获取通过Demo筛选的因子
        with get_session() as session:
            result = session.execute(
                select(Candidate).where(
                    Candidate.symbol == symbol,
                    Candidate.generation == generation,
                    Candidate.status == CandidateStatus.VALIDATED
                )
            )
            candidates = result.scalars().all()

        if not candidates:
            logger.warning(f"没有找到通过Demo筛选的因子: {symbol} 第{generation}代")
            return {
                "total": 0,
                "success": 0,
                "failed": 0
            }

        logger.info(f"找到 {len(candidates)} 个通过Demo筛选的因子")

        # 加载价格数据
        price_data = self._load_price_data(symbol)
        if price_data is None:
            logger.error(f"无法加载价格数据: {symbol}")
            return {
                "total": len(candidates),
                "success": 0,
                "failed": len(candidates)
            }

        # 生成因子值序列
        success_count = 0
        failed_count = 0

        for candidate in candidates:
            try:
                self._generate_single_factor_values(
                    candidate,
                    price_data,
                    symbol
                )
                success_count += 1
                logger.debug(f"成功生成因子值序列: {candidate.id}")
            except Exception as e:
                failed_count += 1
                logger.error(f"生成因子值序列失败: {candidate.id}, 错误: {e}")

        logger.info(
            f"因子值序列生成完成: 总数={len(candidates)}, "
            f"成功={success_count}, 失败={failed_count}"
        )

        return {
            "total": len(candidates),
            "success": success_count,
            "failed": failed_count
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

    def _generate_single_factor_values(
        self,
        candidate: Candidate,
        price_data: Dict[str, np.ndarray],
        symbol: str
    ) -> None:
        """
        生成单个因子的值序列

        Args:
            candidate: 候选因子
            price_data: 价格数据
            symbol: 品种
        """
        from quant_engine.factors.formula_dsl import parse_expr
        from quant_engine.factors.vector_index import VectorizedFactorEvaluator

        # 解析因子公式
        expr = parse_expr(candidate.formula)
        if expr is None:
            raise ValueError(f"无法解析因子公式: {candidate.formula}")

        # 创建评估器
        evaluator = VectorizedFactorEvaluator()

        # 计算因子值
        factor_values = evaluator.evaluate(
            expr,
            price_data["open"],
            price_data["high"],
            price_data["low"],
            price_data["close"],
            price_data["volume"]
        )

        # 保存因子值序列到数据库
        self._save_factor_values(
            candidate.id,
            symbol,
            price_data["timestamp"],
            factor_values
        )

    def _save_factor_values(
        self,
        factor_id: str,
        symbol: str,
        timestamps: np.ndarray,
        factor_values: np.ndarray
    ) -> None:
        """
        保存因子值序列到数据库

        Args:
            factor_id: 因子ID
            symbol: 品种
            timestamps: 时间戳数组
            factor_values: 因子值数组
        """
        from app.models import FactorValueHistory
        from app.db import get_session

        with get_session() as session:
            # 删除旧的因子值序列
            session.execute(
                f"DELETE FROM factor_value_history WHERE factor_id = '{factor_id}'"
            )

            # 批量插入新的因子值序列
            batch_size = 1000
            for i in range(0, len(timestamps), batch_size):
                batch_end = min(i + batch_size, len(timestamps))
                batch_records = [
                    FactorValueHistory(
                        factor_id=factor_id,
                        symbol=symbol,
                        timestamp=timestamps[j],
                        factor_value=factor_values[j]
                    )
                    for j in range(i, batch_end)
                    if not np.isnan(factor_values[j])
                ]
                session.add_all(batch_records)

        logger.debug(f"保存因子值序列: {factor_id}, 数量={len(timestamps)}")

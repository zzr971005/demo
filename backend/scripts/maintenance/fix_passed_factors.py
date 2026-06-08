"""
修复历史 EvolutionTask 的 passed_factors 字段。
Candidate 表无 overfitting_passed 字段，改用 sharpe_val 不为 None 作为过拟合检验通过的代理指标。
"""
import logging
from sqlalchemy import select, func, desc
from app.db import get_session
from app.models import EvolutionTask, Candidate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_passed_factors():
    with get_session() as session:
        # 获取所有有候选因子的 symbol
        symbols = session.execute(
            select(Candidate.symbol).distinct()
        ).scalars().all()

        total_fixed = 0
        for symbol in symbols:
            # 统计该 symbol 有验证夏普（sharpe_val 不为 None）的因子数
            # 作为 overfitting_passed 的代理
            passed_count = session.execute(
                select(func.count(Candidate.id))
                .where(
                    Candidate.symbol == symbol,
                    Candidate.sharpe_val.isnot(None),
                )
            ).scalar() or 0

            total_count = session.execute(
                select(func.count(Candidate.id))
                .where(Candidate.symbol == symbol)
            ).scalar() or 0

            # 找到该 symbol 最新的 EvolutionTask
            task = session.execute(
                select(EvolutionTask)
                .where(EvolutionTask.symbol == symbol)
                .order_by(desc(EvolutionTask.created_at))
                .limit(1)
            ).scalars().first()

            if task:
                old_passed = task.passed_factors or 0
                task.passed_factors = passed_count
                task.total_factors = total_count
                if old_passed != passed_count:
                    total_fixed += 1
                    logger.info(
                        f"[{symbol}] 修复 passed_factors: {old_passed} -> {passed_count} "
                        f"(total_factors: {total_count})"
                    )
            else:
                logger.warning(f"[{symbol}] 无 EvolutionTask 记录，跳过")

        logger.info(f"共修复 {total_fixed} 个任务")


if __name__ == "__main__":
    fix_passed_factors()

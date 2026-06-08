"""
数据完整性检查脚本

检查数据库中的数据完整性问题：
1. 重复的因子表达式
2. 缺失的IC字段
3. 异常的因子值
4. 不一致的代数数据
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Dict, List, Any
from sqlalchemy import select, func, and_

try:
    from app.db import get_session
    from app.models import Candidate, GenerationStats
    # EvolutionFactor model doesn't exist, skip related checks
    EvolutionFactor = None
except ImportError as e:
    print(f"无法导入app模块: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"sys.path: {sys.path}")
    # Only exit if running as standalone script, not when imported
    if __name__ == "__main__":
        sys.exit(1)
    else:
        raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIntegrityChecker:
    """数据完整性检查器"""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []

    def check_all(self) -> Dict[str, Any]:
        """执行所有检查"""
        logger.info("开始数据完整性检查...")

        results = {
            "duplicate_expressions": self.check_duplicate_expressions(),
            "missing_ic_fields": self.check_missing_ic_fields(),
            "abnormal_factor_values": self.check_abnormal_factor_values(),
            "inconsistent_generations": self.check_inconsistent_generations(),
        }

        total_issues = sum(len(v) if isinstance(v, list) else 1 for v in results.values())
        logger.info(f"数据完整性检查完成，共发现 {total_issues} 个问题")

        return results

    def check_duplicate_expressions(self) -> List[Dict[str, Any]]:
        """检查重复的因子表达式"""
        logger.info("检查重复的因子表达式...")
        issues = []

        with get_session() as session:
            # 检查Candidate表中的重复表达式
            result = session.execute(
                select(
                    Candidate.formula,
                    func.count(Candidate.id).label('count')
                ).group_by(Candidate.formula)
                .having(func.count(Candidate.id) > 1)
            )
            duplicates = result.all()

            for expr, count in duplicates:
                issues.append({
                    "type": "duplicate_expression",
                    "table": "candidates",
                    "expression": expr,
                    "count": count,
                    "severity": "high" if count > 5 else "medium"
                })

            # EvolutionFactor model doesn't exist, skip evolution_factors table check
            if EvolutionFactor is not None:
                # 检查EvolutionFactor表中的重复表达式
                result = session.execute(
                    select(
                        EvolutionFactor.expression,
                        func.count(EvolutionFactor.id).label('count')
                    ).group_by(EvolutionFactor.expression)
                    .having(func.count(EvolutionFactor.id) > 1)
                )
                duplicates = result.all()

                for expr, count in duplicates:
                    issues.append({
                        "type": "duplicate_expression",
                        "table": "evolution_factors",
                        "expression": expr,
                        "count": count,
                        "severity": "high" if count > 5 else "medium"
                    })

        logger.info(f"发现 {len(issues)} 个重复表达式问题")
        return issues

    def check_missing_ic_fields(self) -> List[Dict[str, Any]]:
        """检查缺失的IC字段"""
        logger.info("检查缺失的IC字段...")
        issues = []

        with get_session() as session:
            # 检查Candidate表中缺失IC字段的记录
            result = session.execute(
                select(Candidate).where(
                    and_(
                        Candidate.status.in_(['VALIDATED', 'DEPLOYABLE', 'RUNNING']),
                        (Candidate.ic_mean_4h.is_(None)) |
                        (Candidate.ic_mean_24h.is_(None)) |
                        (Candidate.ic_mean_168h.is_(None)) |
                        (Candidate.ic_ir.is_(None)) |
                        (Candidate.ic_half_life.is_(None))
                    )
                )
            )
            candidates = result.scalars().all()

            for candidate in candidates:
                missing_fields = []
                if candidate.ic_mean_4h is None:
                    missing_fields.append("ic_mean_4h")
                if candidate.ic_mean_24h is None:
                    missing_fields.append("ic_mean_24h")
                if candidate.ic_mean_168h is None:
                    missing_fields.append("ic_mean_168h")
                if candidate.ic_ir is None:
                    missing_fields.append("ic_ir")
                if candidate.ic_half_life is None:
                    missing_fields.append("ic_half_life")

                issues.append({
                    "type": "missing_ic_fields",
                    "table": "candidates",
                    "factor_id": candidate.id,
                    "symbol": candidate.symbol,
                    "generation": candidate.generation,
                    "missing_fields": missing_fields,
                    "severity": "medium"
                })

            # EvolutionFactor model doesn't exist, skip evolution_factors table check
            if EvolutionFactor is not None:
                # 检查EvolutionFactor表中缺失IC字段的记录
                result = session.execute(
                    select(EvolutionFactor).where(
                        and_(
                            EvolutionFactor.is_candidate == True,
                            (EvolutionFactor.ic_mean_4h.is_(None)) |
                            (EvolutionFactor.ic_mean_24h.is_(None)) |
                            (EvolutionFactor.ic_mean_168h.is_(None)) |
                            (EvolutionFactor.ic_ir.is_(None)) |
                            (EvolutionFactor.ic_half_life.is_(None))
                        )
                    )
                )
                factors = result.scalars().all()

                for factor in factors:
                    missing_fields = []
                    if factor.ic_mean_4h is None:
                        missing_fields.append("ic_mean_4h")
                    if factor.ic_mean_24h is None:
                        missing_fields.append("ic_mean_24h")
                    if factor.ic_mean_168h is None:
                        missing_fields.append("ic_mean_168h")
                    if factor.ic_ir is None:
                        missing_fields.append("ic_ir")
                    if factor.ic_half_life is None:
                        missing_fields.append("ic_half_life")

                    issues.append({
                        "type": "missing_ic_fields",
                        "table": "evolution_factors",
                        "factor_id": factor.factor_id,
                        "symbol": factor.symbol,
                        "generation": factor.generation,
                        "missing_fields": missing_fields,
                        "severity": "medium"
                    })

        logger.info(f"发现 {len(issues)} 个缺失IC字段问题")
        return issues

    def check_abnormal_factor_values(self) -> List[Dict[str, Any]]:
        """检查异常的因子值"""
        logger.info("检查异常的因子值...")
        issues = []

        with get_session() as session:
            # 检查夏普比率异常（>10或<-5）
            result = session.execute(
                select(Candidate).where(
                    and_(
                        Candidate.sharpe_test.isnot(None),
                        (Candidate.sharpe_test > 10) | (Candidate.sharpe_test < -5)
                    )
                )
            )
            candidates = result.scalars().all()

            for candidate in candidates:
                issues.append({
                    "type": "abnormal_sharpe",
                    "table": "candidates",
                    "factor_id": candidate.id,
                    "symbol": candidate.symbol,
                    "sharpe": candidate.sharpe_test,
                    "severity": "high"
                })

            # 检查IC值异常（>1或<-1）
            result = session.execute(
                select(Candidate).where(
                    and_(
                        Candidate.ic_mean_24h.isnot(None),
                        (Candidate.ic_mean_24h > 1) | (Candidate.ic_mean_24h < -1)
                    )
                )
            )
            candidates = result.scalars().all()

            for candidate in candidates:
                issues.append({
                    "type": "abnormal_ic",
                    "table": "candidates",
                    "factor_id": candidate.id,
                    "symbol": candidate.symbol,
                    "ic_mean_24h": candidate.ic_mean_24h,
                    "severity": "high"
                })

            # 检查IC半衰期异常（>336小时或<0）
            result = session.execute(
                select(Candidate).where(
                    and_(
                        Candidate.ic_half_life.isnot(None),
                        (Candidate.ic_half_life > 336) | (Candidate.ic_half_life < 0)
                    )
                )
            )
            candidates = result.scalars().all()

            for candidate in candidates:
                issues.append({
                    "type": "abnormal_half_life",
                    "table": "candidates",
                    "factor_id": candidate.id,
                    "symbol": candidate.symbol,
                    "ic_half_life": candidate.ic_half_life,
                    "severity": "medium"
                })

        logger.info(f"发现 {len(issues)} 个异常因子值问题")
        return issues

    def check_inconsistent_generations(self) -> List[Dict[str, Any]]:
        """检查不一致的代数数据"""
        logger.info("检查不一致的代数数据...")
        issues = []

        with get_session() as session:
            # 检查GenerationStats表中缺失的代数
            result = session.execute(
                select(GenerationStats.symbol, func.max(GenerationStats.generation).label('max_gen'))
                .group_by(GenerationStats.symbol)
            )
            max_gens = {row.symbol: row.max_gen for row in result.all()}

            # 检查是否有断层的代数
            for symbol, max_gen in max_gens.items():
                if max_gen > 10:  # 只检查代数大于10的
                    result = session.execute(
                        select(GenerationStats.generation).where(
                            GenerationStats.symbol == symbol
                        ).order_by(GenerationStats.generation)
                    )
                    existing_gens = [row.generation for row in result.all()]

                    expected_gens = set(range(max_gen + 1))
                    missing_gens = sorted(expected_gens - set(existing_gens))

                    if missing_gens:
                        issues.append({
                            "type": "missing_generations",
                            "table": "generation_stats",
                            "symbol": symbol,
                            "missing_generations": missing_gens,
                            "severity": "low"
                        })

            # EvolutionFactor model doesn't exist, skip evolution_factors table check
            if EvolutionFactor is not None:
                # 检查EvolutionFactor表中代数超出GenerationStats最大代数的记录
                for symbol, max_gen in max_gens.items():
                    result = session.execute(
                        select(EvolutionFactor).where(
                            and_(
                                EvolutionFactor.symbol == symbol,
                                EvolutionFactor.generation > max_gen
                            )
                        )
                    )
                    factors = result.scalars().all()

                    for factor in factors:
                        issues.append({
                            "type": "generation_beyond_stats",
                            "table": "evolution_factors",
                            "factor_id": factor.factor_id,
                            "symbol": symbol,
                            "generation": factor.generation,
                            "max_generation_in_stats": max_gen,
                            "severity": "medium"
                        })

        logger.info(f"发现 {len(issues)} 个代数不一致问题")
        return issues

    def print_report(self, results: Dict[str, Any]):
        """打印检查报告"""
        print("\n" + "="*60)
        print("数据完整性检查报告")
        print("="*60)

        for check_name, issues in results.items():
            print(f"\n{check_name.replace('_', ' ').title()}:")
            print(f"  发现问题: {len(issues)}")

            if issues:
                for issue in issues[:10]:  # 只显示前10个
                    severity = issue.get('severity', 'unknown')
                    print(f"  - [{severity.upper()}] {issue}")
                if len(issues) > 10:
                    print(f"  ... 还有 {len(issues) - 10} 个问题未显示")

        print("\n" + "="*60)


if __name__ == "__main__":
    checker = DataIntegrityChecker()
    results = checker.check_all()
    checker.print_report(results)

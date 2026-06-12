"""
策略轮换器 - 策略轮换机制

负责：
- 判断是否应该轮换策略
- 执行策略轮换
- 记录轮换历史
- 定时轮换任务
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .strategy_selector import calculate_composite_score, calculate_factor_correlation

logger = logging.getLogger(__name__)


def should_rotate_strategy(
    current_factor: Dict[str, Any],
    new_factor: Dict[str, Any],
    config: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    判断是否应该轮换策略
    
    Parameters
    ----------
    current_factor : Dict[str, Any]
        当前策略因子
    new_factor : Dict[str, Any]
        新候选因子
    config : Dict[str, Any]
        轮换配置
    
    Returns
    -------
    Tuple[bool, str]
        (是否轮换, 原因)
    """
    rotation_config = config.get("rotation", {})
    score_threshold = rotation_config.get("score_improvement_threshold", 0.1)
    correlation_threshold = rotation_config.get("correlation_threshold", 0.3)
    
    # 条件1：评分提升
    current_score = calculate_composite_score(current_factor)
    new_score = calculate_composite_score(new_factor)
    
    if current_score == 0:
        improvement = 0
    else:
        improvement = (new_score - current_score) / current_score
    
    if improvement < score_threshold:
        return False, f"评分提升不足 ({improvement:.1%} < {score_threshold:.1%})"
    
    # 条件2：相关性低
    correlation = calculate_factor_correlation(current_factor, new_factor)
    if correlation > correlation_threshold:
        return False, f"相关性过高 ({correlation:.2f} > {correlation_threshold:.2f})"
    
    # 条件3：样本外表现
    sharpe_test_current = current_factor.get("sharpe_test", 0) or 0
    sharpe_test_new = new_factor.get("sharpe_test", 0) or 0
    
    if sharpe_test_new < sharpe_test_current * 0.8:
        return False, f"样本外表现差 (sharpe_test: {sharpe_test_new:.2f} < {sharpe_test_current * 0.8:.2f})"
    
    return True, f"评分提升{improvement:.1%}"


class StrategyRotator:
    """策略轮换器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化策略轮换器
        
        Parameters
        ----------
        config : Dict[str, Any]
            配置字典
        """
        self.config = config or {}
        self.rotation_enabled = self.config.get("rotation", {}).get("enabled", True)
        self.rotation_period_days = self.config.get("rotation", {}).get("period_days", 14)
        self.freeze_period_days = self.config.get("rotation", {}).get("freeze_period_days", 14)
    
    def execute_rotation(
        self,
        symbol: str,
        current_strategies: List[Dict[str, Any]],
        top_factors: List[Dict[str, Any]],
        db_session
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        执行策略轮换
        
        Parameters
        ----------
        symbol : str
            品种代码
        current_strategies : List[Dict[str, Any]]
            当前策略列表
        top_factors : List[Dict[str, Any]]
            最优因子池
        db_session
            数据库会话
        
        Returns
        -------
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]
            (新策略列表, 轮换历史记录)
        """
        from .strategy_selector import select_top_strategies
        from ..core.models.evolution import StrategyRotationHistory
        
        rotation_history = []
        
        # 1. 重新选择策略
        new_strategies = select_top_strategies(
            top_factors,
            count=len(current_strategies),
            category_distribution=self.config.get("strategy_selection", {}).get("category_distribution", {"fast": 2, "medium": 2, "slow": 1})
        )
        
        # 2. 对比并轮换
        for i, (old, new) in enumerate(zip(current_strategies, new_strategies)):
            should_rotate, reason = should_rotate_strategy(old, new, self.config)
            
            if should_rotate:
                # 执行轮换
                old_id = old.get("id")
                new_id = new.get("id")
                
                # 更新数据库标记
                from app.models import Candidate
                if old_id:
                    old_candidate = db_session.query(Candidate).filter(Candidate.id == old_id).first()
                    if old_candidate:
                        old_candidate.is_selected_strategy = False
                        old_candidate.strategy_rank = None
                
                if new_id:
                    new_candidate = db_session.query(Candidate).filter(Candidate.id == new_id).first()
                    if new_candidate:
                        new_candidate.is_selected_strategy = True
                        new_candidate.strategy_rank = i + 1
                
                # 记录轮换历史
                current_score = calculate_composite_score(old)
                new_score = calculate_composite_score(new)
                improvement = new_score - current_score
                
                rotation_record = StrategyRotationHistory.add_rotation_record(
                    db_session,
                    symbol=symbol,
                    old_factor_id=old_id,
                    new_factor_id=new_id,
                    rotation_reason=reason,
                    score_improvement=improvement
                )
                
                rotation_history.append(rotation_record.to_dict())
                
                logger.info(f"策略轮换: {symbol} - {old_id} -> {new_id}, 原因: {reason}")
        
        db_session.commit()
        
        return new_strategies, rotation_history
    
    def check_rotation_needed(self, symbol: str, last_rotation_date: Optional[datetime]) -> bool:
        """
        检查是否需要轮换
        
        Parameters
        ----------
        symbol : str
            品种代码
        last_rotation_date : Optional[datetime]
            上次轮换日期
        
        Returns
        -------
        bool
            是否需要轮换
        """
        if not self.rotation_enabled:
            return False
        
        if last_rotation_date is None:
            return True
        
        days_since_rotation = (datetime.now() - last_rotation_date).days
        
        return days_since_rotation >= self.rotation_period_days


def get_current_strategies(db_session, symbol: str) -> List[Dict[str, Any]]:
    """
    获取当前策略
    
    Parameters
    ----------
    db_session
        数据库会话
    symbol : str
        品种代码
    
    Returns
    -------
    List[Dict[str, Any]]
        当前策略列表
    """
    from app.models import Candidate
    
    strategies = db_session.query(Candidate).filter(
        Candidate.symbol == symbol,
        Candidate.is_selected_strategy == True
    ).order_by(Candidate.strategy_rank).all()
    
    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "formula": s.formula,
            "sharpe_train": s.sharpe_train,
            "sharpe_test": s.sharpe_test,
            "calmar": s.calmar,
            "max_drawdown": s.max_drawdown,
            "win_rate": s.win_rate,
            "total_trades": s.total_trades,
            "ic_mean_4h": s.ic_mean_4h,
            "ic_mean_24h": s.ic_mean_24h,
            "ic_mean_168h": s.ic_mean_168h,
            "ic_std": s.ic_std,
            "ic_ir": s.ic_ir,
            "ic_half_life": s.ic_half_life,
            "factor_category": s.factor_category,
            "strategy_rank": s.strategy_rank,
        }
        for s in strategies
    ]


def get_top_factors(db_session, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    获取最优因子池
    
    Parameters
    ----------
    db_session
        数据库会话
    symbol : str
        品种代码
    limit : int
        因子数量
    
    Returns
    -------
    List[Dict[str, Any]]
        最优因子列表
    """
    from app.models import Candidate, CandidateStatus
    
    factors = db_session.query(Candidate).filter(
        Candidate.symbol == symbol,
        Candidate.status.in_([
            CandidateStatus.DEPLOYABLE,
            CandidateStatus.RUNNING,
            CandidateStatus.PAPER,
            CandidateStatus.VALIDATED,
        ])
    ).order_by(Candidate.sharpe_test.desc()).limit(limit).all()
    
    return [
        {
            "id": f.id,
            "symbol": f.symbol,
            "formula": f.formula,
            "sharpe_train": f.sharpe_train,
            "sharpe_test": f.sharpe_test,
            "calmar": f.calmar,
            "max_drawdown": f.max_drawdown,
            "win_rate": f.win_rate,
            "total_trades": f.total_trades,
            "ic_mean_4h": f.ic_mean_4h,
            "ic_mean_24h": f.ic_mean_24h,
            "ic_mean_168h": f.ic_mean_168h,
            "ic_std": f.ic_std,
            "ic_ir": f.ic_ir,
            "ic_half_life": f.ic_half_life,
            "factor_category": f.factor_category,
        }
        for f in factors
    ]

"""
自动策略替换API
基于验证结果自动切换策略
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import asyncio

from app.db import get_session
from app.models import Candidate, CandidateStatus

router = APIRouter(prefix="/strategy", tags=["strategy"])


class StrategyPerformance(BaseModel):
    """策略性能"""
    strategy_id: str
    symbol: str
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_return: float
    trade_count: int
    last_updated: datetime


class ReplacementCandidate(BaseModel):
    """替换候选"""
    current_strategy: str
    candidate_strategy: str
    symbol: str
    reason: str
    confidence: float
    performance_improvement: float
    risk_score: float


class ReplacementRequest(BaseModel):
    """替换请求"""
    symbol: str
    current_strategy: str
    new_strategy: str
    reason: Optional[str] = None
    auto_confirm: bool = False


class ReplacementResult(BaseModel):
    """替换结果"""
    success: bool
    symbol: str
    old_strategy: str
    new_strategy: str
    timestamp: datetime
    reason: str
    transaction_id: str


class ReplacementRule(BaseModel):
    """替换规则"""
    rule_id: str
    name: str
    description: str
    condition: str
    action: str
    priority: int
    enabled: bool
    created_at: datetime


# 替换规则（内存存储）
replacement_rules: List[ReplacementRule] = []
replacement_history: List[ReplacementResult] = []


# 初始化默认规则
def init_default_rules():
    """初始化默认替换规则"""
    global replacement_rules
    replacement_rules = [
        ReplacementRule(
            rule_id="rule_001",
            name="夏普比率阈值",
            description="当策略夏普比率低于0.8时触发替换",
            condition="sharpe_ratio < 0.8",
            action="replace_with_best_candidate",
            priority=1,
            enabled=True,
            created_at=datetime.now()
        ),
        ReplacementRule(
            rule_id="rule_002",
            name="最大回撤阈值",
            description="当策略最大回撤超过15%时触发替换",
            condition="max_drawdown > 0.15",
            action="replace_with_lowest_drawdown",
            priority=2,
            enabled=True,
            created_at=datetime.now()
        ),
        ReplacementRule(
            rule_id="rule_003",
            name="胜率阈值",
            description="当策略胜率低于45%时触发替换",
            condition="win_rate < 0.45",
            action="replace_with_highest_winrate",
            priority=3,
            enabled=True,
            created_at=datetime.now()
        ),
        ReplacementRule(
            rule_id="rule_004",
            name="过拟合检测",
            description="当策略过拟合指标不通过时触发替换",
            condition="overfitting_passed = False",
            action="stop_and_wait",
            priority=0,
            enabled=True,
            created_at=datetime.now()
        )
    ]


init_default_rules()


@router.get("/performance/{symbol}", response_model=List[StrategyPerformance])
async def get_strategy_performance(symbol: str):
    """
    获取品种的策略性能列表（从数据库读取真实进化因子）
    
    Args:
        symbol: 品种代码
    
    Returns:
        策略性能列表
    """
    try:
        with get_session() as session:
            # 查询该品种的所有候选策略
            candidates = session.query(Candidate)\
                .filter(Candidate.symbol == symbol)\
                .filter(Candidate.status != CandidateStatus.RETIRED)\
                .order_by(Candidate.created_at.desc())\
                .limit(20)\
                .all()
            
            performances = []
            for candidate in candidates:
                # 使用实际的总收益率
                total_return = candidate.total_return or 0.0
                
                performances.append(StrategyPerformance(
                    strategy_id=candidate.id,
                    symbol=candidate.symbol,
                    sharpe_ratio=candidate.sharpe_train or 0.0,
                    max_drawdown=candidate.max_drawdown or 0.0,
                    win_rate=candidate.win_rate or 0.0,
                    total_return=total_return,
                    trade_count=candidate.total_trades or 0,
                    last_updated=candidate.updated_at
                ))
            
            return performances
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询策略性能失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询策略性能失败: {str(e)}")


@router.get("/candidates/{symbol}", response_model=List[ReplacementCandidate])
async def get_replacement_candidates(symbol: str):
    """
    获取替换候选列表（基于真实数据库数据）
    
    Args:
        symbol: 品种代码
    
    Returns:
        替换候选列表
    """
    performances = await get_strategy_performance(symbol)
    
    if not performances:
        return []
    
    # 按夏普比率排序
    sorted_perf = sorted(performances, key=lambda x: x.sharpe_ratio, reverse=True)
    
    if len(sorted_perf) < 2:
        return []
    
    # 找到当前运行中的策略（状态为RUNNING的）
    current_strategy = None
    with get_session() as session:
        running = session.query(Candidate)\
            .filter(Candidate.symbol == symbol)\
            .filter(Candidate.status == CandidateStatus.RUNNING)\
            .first()
        if running:
            current_strategy = running.id
    
    # 如果没有运行中的策略，取最差的作为当前策略
    if not current_strategy:
        current_strategy = sorted_perf[-1].strategy_id
    
    candidates = []
    current_perf = next((p for p in sorted_perf if p.strategy_id == current_strategy), None)
    
    if not current_perf:
        return []
    
    # 找到更好的候选策略
    for perf in sorted_perf:
        if perf.strategy_id == current_strategy:
            continue
        
        # 计算性能提升
        if perf.sharpe_ratio > current_perf.sharpe_ratio:
            improvement = (perf.sharpe_ratio - current_perf.sharpe_ratio) / max(current_perf.sharpe_ratio, 0.001)
            
            # 计算置信度（基于夏普差异和回撤风险）
            drawdown_diff = current_perf.max_drawdown - perf.max_drawdown
            confidence = min(0.99, 0.6 + improvement * 2 + drawdown_diff * 0.5)
            
            candidates.append(ReplacementCandidate(
                current_strategy=current_strategy,
                candidate_strategy=perf.strategy_id,
                symbol=symbol,
                reason=f"夏普比率从 {current_perf.sharpe_ratio:.2f} 提升至 {perf.sharpe_ratio:.2f}",
                confidence=round(confidence, 2),
                performance_improvement=round(improvement, 4),
                risk_score=round(perf.max_drawdown or 0.0, 2)
            ))
    
    # 按置信度排序
    candidates.sort(key=lambda x: x.confidence, reverse=True)
    return candidates


@router.post("/replace", response_model=ReplacementResult)
async def replace_strategy(request: ReplacementRequest, background_tasks: BackgroundTasks):
    """
    执行策略替换
    
    Args:
        request: 替换请求
        background_tasks: 后台任务
    
    Returns:
        替换结果
    """
    try:
        with get_session() as session:
            # 更新数据库状态
            # 1. 将旧策略标记为DEGRADED
            old_candidate = session.query(Candidate)\
                .filter(Candidate.id == request.current_strategy)\
                .first()
            if old_candidate:
                old_candidate.status = CandidateStatus.DEGRADED
                old_candidate.degraded_at = datetime.now()
                old_candidate.retire_reason = request.reason or "策略替换"
            
            # 2. 将新策略标记为RUNNING
            new_candidate = session.query(Candidate)\
                .filter(Candidate.id == request.new_strategy)\
                .first()
            if new_candidate:
                new_candidate.status = CandidateStatus.RUNNING
                new_candidate.deployed_at = datetime.now()
        
        transaction_id = f"txn_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 后台执行替换
        if request.auto_confirm:
            background_tasks.add_task(execute_replacement, request, transaction_id)
        
        result = ReplacementResult(
            success=True,
            symbol=request.symbol,
            old_strategy=request.current_strategy,
            new_strategy=request.new_strategy,
            timestamp=datetime.now(),
            reason=request.reason or "手动触发",
            transaction_id=transaction_id
        )
        
        replacement_history.append(result)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行策略替换失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"执行策略替换失败: {str(e)}")


async def execute_replacement(request: ReplacementRequest, transaction_id: str):
    """后台执行策略替换"""
    # 模拟执行过程（实际应连接交易引擎）
    await asyncio.sleep(2)
    logger.info(f"[{transaction_id}] 策略替换完成: {request.current_strategy} -> {request.new_strategy}")


@router.get("/rules", response_model=List[ReplacementRule])
async def get_replacement_rules():
    """获取替换规则列表"""
    return replacement_rules


@router.put("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, enabled: bool):
    """启用/禁用替换规则"""
    for rule in replacement_rules:
        if rule.rule_id == rule_id:
            rule.enabled = enabled
            return {"success": True, "rule_id": rule_id, "enabled": enabled}
    
    raise HTTPException(status_code=404, detail="Rule not found")


@router.get("/history", response_model=List[ReplacementResult])
async def get_replacement_history(symbol: Optional[str] = None):
    """获取替换历史"""
    if symbol:
        return [h for h in replacement_history if h.symbol == symbol]
    return replacement_history


@router.post("/auto-check/{symbol}")
async def auto_check_replacement(symbol: str, background_tasks: BackgroundTasks):
    """
    自动检查是否需要策略替换
    
    Args:
        symbol: 品种代码
        background_tasks: 后台任务
    
    Returns:
        检查结果
    """
    candidates = await get_replacement_candidates(symbol)
    
    # 筛选需要替换的候选（置信度>0.7）
    need_replacement = [c for c in candidates if c.confidence > 0.7]
    
    if need_replacement:
        # 自动执行置信度最高的替换
        best_candidate = max(need_replacement, key=lambda x: x.confidence)
        
        background_tasks.add_task(
            execute_replacement,
            ReplacementRequest(
                symbol=symbol,
                current_strategy=best_candidate.current_strategy,
                new_strategy=best_candidate.candidate_strategy,
                reason=best_candidate.reason,
                auto_confirm=True
            ),
            f"auto_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        return {
            "need_replacement": True,
            "candidate": best_candidate,
            "auto_triggered": True,
            "message": f"自动触发替换: {best_candidate.reason}"
        }
    
    return {
        "need_replacement": False,
        "message": "当前策略表现良好，无需替换",
        "candidates_count": len(candidates)
    }


@router.get("/status/{symbol}")
async def get_strategy_status(symbol: str):
    """获取策略状态"""
    try:
        with get_session() as session:
            # 获取当前运行中的策略
            running = session.query(Candidate)\
                .filter(Candidate.symbol == symbol)\
                .filter(Candidate.status == CandidateStatus.RUNNING)\
                .first()
            
            # 获取候选策略数量
            candidate_count = session.query(Candidate)\
                .filter(Candidate.symbol == symbol)\
                .filter(Candidate.status == CandidateStatus.CANDIDATE)\
                .count()
            
            # 计算性能分数
            performance_score = 0.85
            if running and running.sharpe_train:
                performance_score = min(1.0, running.sharpe_train / 1.5)
            
            return {
                "symbol": symbol,
                "current_strategy": running.id if running else "none",
                "status": "running" if running else "stopped",
                "performance_score": round(performance_score, 2),
                "risk_level": "low" if (running and running.max_drawdown and running.max_drawdown < 0.1) else "medium",
                "last_check": datetime.now(),
                "next_check": datetime.now(),
                "replacement_candidates": candidate_count,
                "auto_replacement_enabled": True
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取策略状态失败: {str(e)}")
